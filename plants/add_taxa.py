#!/usr/bin/env python3
"""Use binomial species names but single taxon names for higher and lower ranks."""
import argparse
import csv
import os
import shutil
import sqlite3
import sys
import textwrap
from collections import defaultdict
from collections import namedtuple
from pathlib import Path

import regex
from pylib import const
from tqdm import tqdm
from traiter.pylib import log

Record = namedtuple("Record", "term_set label pattern attr replace extra1 extra2")


class Ranks:
    def __init__(self):
        self.ranks = self.get_ranks()
        self.id2rank = {int(r["extra1"]): r["replace"] for r in self.ranks}
        self.pattern2rank = {r["pattern"]: r["replace"] for r in self.ranks}
        self.rank2id = {r["pattern"]: int(r["extra1"]) for r in self.ranks}
        self.all = {r["pattern"] for r in self.ranks}
        self.lower = {r for i, r in self.id2rank.items() if i > const.ITIS_SPECIES_ID}
        self.higher = {r for i, r in self.id2rank.items() if i < const.ITIS_SPECIES_ID}
        self.abbrev_list = defaultdict(set)
        for rank in self.ranks:
            self.abbrev_list[rank["replace"]].add(rank["pattern"])

    def normalize_rank(self, rank):
        rank = rank.lower()
        return self.pattern2rank.get(rank, "")

    @staticmethod
    def get_ranks():
        with sqlite3.connect(const.TERM_DB) as cxn:
            cxn.row_factory = sqlite3.Row
            sql = "select * from terms where term_set = 'ranks'"
            ranks = [t for t in cxn.execute(sql)]
        return ranks

    def has_rank_abbrev(self, rank, pattern):
        return any(w in self.abbrev_list[rank] for w in pattern.split())


class Taxa:
    def __init__(self, ranks):
        self.ranks = ranks
        self.raw = defaultdict(set)  # Terms with possibly multiple ranks
        self.taxa = {}  # Taxon terms with a single rank
        self.terms = {}  # Terms that go into the DB
        self.valid_pattern = regex.compile(r"^\p{L}[\p{L}\s'.-]*\p{L}$")
        self.min_pattern_len = 3
        self.min_word_len = 2

    def add_taxon_rank(self, pattern, rank):
        pattern = pattern.lower()
        rank = rank.lower()
        if not self.valid_pattern.match(pattern) or len(pattern) < self.min_pattern_len:
            return
        if any(len(w) < self.min_word_len for w in pattern.split()):
            return
        if rank not in self.ranks.pattern2rank:
            return
        self.raw[pattern].add(rank)

    def add_taxon_ranks(self, pattern, ranks):
        for rank in ranks:
            self.add_taxon_rank(pattern, rank)

    @staticmethod
    def abbreviate(pattern):
        genus, *parts = pattern.split()
        abbrev = genus[0].upper() + "."
        abbrev = " ".join([abbrev] + parts)
        return abbrev

    def resolve_ranks(self):
        """Choose only one rank per taxon."""
        for pattern, ranks in self.raw.items():
            if len(ranks) == 1:
                rank = ranks.pop()
            else:
                word_count = len(pattern.split())
                if "species" in ranks and "variety" in ranks and word_count == 2:
                    rank = "species"
                elif "species" in ranks and "variety" in ranks and word_count > 2:
                    rank = "variety"
                elif "genus" in ranks:
                    rank = "genus"
                elif "division" in ranks:
                    rank = "division"
                elif "family" in ranks:
                    rank = "family"
                elif "suborder" in ranks:
                    rank = "suborder"
                elif all(r in RANKS.lower for r in ranks):
                    rank = "subspecies"
                elif "subspecies" in ranks:
                    rank = "subspecies"
                elif "variety" in ranks:
                    rank = "variety"
                elif "section" in ranks:
                    rank = "section"
                else:
                    rank = "error"
                    print(
                        f"Unhandled multiple ranks: {pattern} {ranks}", file=sys.stderr
                    )
            self.taxa[pattern] = rank

    def fix_species(self):
        new = {}
        for pattern, rank in self.taxa.items():
            if rank != "species":
                new[pattern] = rank
            else:
                wc = len(pattern.split())
                if wc < 2:
                    pass
                elif wc == 2:
                    new[pattern] = rank
                elif wc > 2 and RANKS.has_rank_abbrev("section", pattern):
                    pass
                elif wc > 2 and RANKS.has_rank_abbrev("variety", pattern):
                    new[pattern] = "variety"
                elif wc > 2 and RANKS.has_rank_abbrev("form", pattern):
                    new[pattern] = "form"
                elif wc == 3:
                    new[pattern] = "subspecies"
        self.taxa = new

    def add_missing_species(self):
        """Add species that are in trinomials but not in the binomials."""
        new = {}
        for pattern, rank in self.taxa.items():
            new[pattern] = rank
            if rank in RANKS.lower:
                words = pattern.split()
                if len(words) < 2:
                    continue
                species = " ".join(words[:2])
                new[species] = "species"
        self.taxa = new

    def remove_problem_taxa(self):
        """Some upper taxa interfere with other parses."""
        problem_taxa = """ side """.split()
        for problem in problem_taxa:
            del self.taxa[problem]

    def split_words(self):
        """Convert full taxa names into terms for the DB."""
        bad_taxa = ("temp", "uncertain", "unknown")

        # Have higher taxa block lower taxa from getting in
        taxa = sorted(self.taxa.items(), key=lambda t: self.ranks.rank2id[t[1]])

        for taxon, rank in taxa:
            words = taxon.split()

            if any(w in bad_taxa for w in words):
                continue

            words = [w for w in words if w not in self.terms]
            words = [w for w in words if w not in self.ranks.all]

            if rank == "species":
                self.terms[taxon] = rank
            else:
                for word in words:
                    self.terms[word] = rank

    def higher(self):
        for taxon, rank in self.terms.items():
            if rank in self.ranks.higher:
                yield taxon.title(), rank

    def lower(self):
        for taxon, rank in self.terms.items():
            if rank in self.ranks.lower:
                yield taxon.lower(), rank

    def species(self):
        for taxon, rank in self.terms.items():
            if rank == "species":
                name = taxon[0].upper() + taxon[1:]
                yield name, rank


RANKS = Ranks()
TAXA = Taxa(RANKS)


def main():
    log.started()

    args = parse_args()
    get_raw_taxa(args)

    TAXA.resolve_ranks()

    TAXA.fix_species()
    TAXA.add_missing_species()
    TAXA.remove_problem_taxa()
    TAXA.split_words()

    higher = get_higher_taxa()
    species = get_species()
    lower = get_lower_taxa()

    create_tables()
    insert_ranks()

    batch = higher + species + lower
    write_database(batch)

    move_db()

    log.finished()


def get_higher_taxa():
    records = []
    for taxon, rank in tqdm(TAXA.higher(), desc="higher"):
        records.append(
            Record(
                term_set="taxa",
                label="higher_taxon",
                pattern=taxon.lower(),
                attr="lower",
                replace=taxon,
                extra1=rank,
                extra2="",
            )
        )
    return records


def get_lower_taxa():
    records = []
    for taxon, ranks in tqdm(TAXA.lower(), desc="lower"):
        records.append(
            Record(
                term_set="taxa",
                label="lower_taxon",
                pattern=taxon.lower(),
                attr="text",
                replace="",
                extra1="",
                extra2="",
            )
        )
    return records


def get_species():
    species = []
    all_abbrevs = defaultdict(set)

    for taxon, rank in tqdm(TAXA.species(), desc="species 1"):
        species.append(
            Record(
                term_set="taxa",
                label="species_taxon",
                pattern=taxon.lower(),
                attr="lower",
                replace=taxon,
                extra1=rank,
                extra2="",
            )
        )
        abbrev = TAXA.abbreviate(taxon)
        all_abbrevs[abbrev].add(taxon)

    for abbrev, options in tqdm(all_abbrevs.items(), desc="species 2"):
        replace = options.pop() if len(options) == 1 else ""
        options = ",".join(sorted(options)) if len(options) > 1 else ""
        species.append(
            Record(
                term_set="taxa",
                label="species_taxon",
                pattern=abbrev.lower(),
                attr="lower",
                replace=replace,
                extra1="species",
                extra2=options,
            )
        )

    return species


def move_db():
    src = const.FULL_TAXON_DB
    dst = (const.DATA_DIR / "taxa.sqlite").absolute()
    dst.unlink(missing_ok=True)
    shutil.move(src, dst)
    os.symlink(dst, src)


def write_database(batch):
    insert = """
        insert into terms
               ( term_set,  label,  pattern,  attr,  replace,  extra1,  extra2)
        values (:term_set, :label, :pattern, :attr, :replace, :extra1, :extra2)
        """
    with sqlite3.connect(const.FULL_TAXON_DB) as cxn:
        cxn.executemany(insert, batch)


def create_tables():
    const.FULL_TAXON_DB.unlink(missing_ok=True)
    create = """
        create table terms (
            term_set text,
            label    text,
            pattern  text,
            attr     text,
            replace  text,
            extra1   blob,
            extra2   blob
        );
        create table term_columns (
            term_set text,
            extra    text,
            rename   text
        );
        """
    with sqlite3.connect(const.FULL_TAXON_DB) as cxn:
        cxn.executescript(create)


def insert_ranks():
    with sqlite3.connect(const.FULL_TAXON_DB) as cxn:
        cxn.execute(f"attach database '{const.TERM_DB}' as aux")
        sql = """
            insert into term_columns
            select * from aux.term_columns where term_set in ('taxa', 'ranks')"""
        cxn.execute(sql)
        sql = "insert into terms select * from aux.terms where term_set = 'ranks'"
        cxn.execute(sql)


def get_raw_taxa(args):
    if args.itis_db:
        get_itis_taxa(args.itis_db)

    if args.wcvp_file:
        get_wcvp_taxa(args.wcvp_file)

    if args.wfot_tsv:
        get_wfot_taxa(args.wfot_tsv)

    if args.old_db:
        get_old_taxa(args.old_db)

    if args.other_csv:
        get_other_taxa(args.other_csv)


def get_other_taxa(other_csv):
    with open(other_csv) as in_file:
        reader = csv.DictReader(in_file)
        for row in tqdm(reader, desc="other"):
            TAXA.add_taxon_rank(row["taxon"], row["rank"])


def get_old_taxa(old_db):
    with sqlite3.connect(old_db) as cxn:
        cxn.row_factory = sqlite3.Row
        sql = "select * from terms where term_set = 'plant_taxa'"
        rows = [t for t in tqdm(cxn.execute(sql), desc="old DB")]
        for row in rows:
            pattern = row["pattern"]
            ranks = set(row["extra1"].split())
            ranks -= {"species"}
            if not ranks:
                continue
            if all(r in RANKS.lower for r in ranks):
                TAXA.add_taxon_ranks(pattern, ranks)
            elif len(ranks) == 1 and all(r in RANKS.higher for r in ranks):
                TAXA.add_taxon_rank(pattern, ranks.pop())


def get_wfot_taxa(wfot_tsv):
    with open(wfot_tsv) as in_file:
        reader = csv.DictReader(in_file, delimiter="\t")
        for row in tqdm(reader, desc="wfot"):
            rank = RANKS.normalize_rank(row["taxonRank"])
            pattern = row["scientificName"]
            TAXA.add_taxon_rank(pattern, rank)


def get_wcvp_taxa(wcvp_file):
    with open(wcvp_file) as in_file:
        reader = csv.DictReader(in_file, delimiter="|")
        for row in tqdm(reader, desc="wcvp"):
            rank = RANKS.normalize_rank(row["taxonrank"])
            pattern = row["scientfiicname"]
            TAXA.add_taxon_rank(pattern, rank)


def get_itis_taxa(itis_db):
    itis_kingdom_id = 3

    with sqlite3.connect(itis_db) as cxn:
        cxn.row_factory = sqlite3.Row
        sql = "select complete_name, rank_id from taxonomic_units where kingdom_id = ?"
        rows = [t for t in tqdm(cxn.execute(sql, (itis_kingdom_id,)), desc="itis")]

    for row in rows:
        rank, pattern = RANKS.id2rank[row["rank_id"]], row["complete_name"]
        TAXA.add_taxon_rank(pattern, rank)


def parse_args():
    description = """Build a database taxon patterns."""
    arg_parser = argparse.ArgumentParser(
        description=textwrap.dedent(description), fromfile_prefix_chars="@"
    )

    arg_parser.add_argument(
        "--itis-db",
        type=Path,
        metavar="PATH",
        help="""Get terms from this ITIS database.""",
    )

    arg_parser.add_argument(
        "--wcvp-file",
        type=Path,
        metavar="PATH",
        help="""Get terms from this WCVP file. It is '|' a separated CSV.""",
    )

    arg_parser.add_argument(
        "--wfot-tsv",
        type=Path,
        metavar="PATH",
        help="""Get terms from this WFO Taxonomic TSV.""",
    )

    arg_parser.add_argument(
        "--old-db",
        type=Path,
        metavar="PATH",
        help="""Get terms from this old database.""",
    )

    arg_parser.add_argument(
        "--other-csv",
        type=Path,
        metavar="PATH",
        help="""Get terms from this CSV file.""",
    )

    args = arg_parser.parse_args()
    return args


if __name__ == "__main__":
    main()