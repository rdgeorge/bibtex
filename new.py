#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module reads all .pdf files in its directory and produces a .bib file
(default: articles.bib), containing BibTeX extries for all pdfs possible.
"""

from __future__ import print_function, unicode_literals
import argparse
import glob
import os
import re
import subprocess
import sys
try:
    import urllib
    import urllib.request as req
    from urllib.parse import quote
except ImportError:
    from urllib import quote
    import urllib2 as req
    import codecs
    reload(sys)  # Hack to put setdefaultencoding back in after python startup
    sys.setdefaultencoding('utf-8')  # Output utf-8 to teminal


class BibtexFile:

    def __init__(self, path=''):
        self.path = path
        self.entries = []
        self.fill_entries()

    def __contains__(self, item):
        #return item in self.entries
        return repr(item) in self.entries

    def append(self, item):
        pass

    def fill_entries(self):
        pass

    def write_to_file(self):
        #self.entries.sort()
        pass


class Article:

    def __init__(self, path=None):
        self.path = path
        self.authors = []
        self.reference = None
        self.url = None
        self.identifier = None
        self.identifier_type = None
        if path is not None:
            self.identifier, self.identifier_type = self.extract_from_article()
            print(self.identifier, self.identifier_type)
            self.url = self.bibtex_url('esoads.eso.org')
            print(self.url)
            self.get_bibtex('esoads.eso.org')
            print(self.year)
            print(self.title)
            print(self.journal)
            print(self.authors)
            print(self.url)

    def __repr__(self):
        return self.reference

    def extract_info(self):
        """
        Extract identifying information from a text file converted from a pdf

        Parameters:
        -----------
        txt_file: string
            The path to a text file to extract information from

        Returns:
        --------
        tuple: 2 elements, (identifier type, value)
            identifier type can be {'doi', arxiv', 'abs'}
        """
        txt = 'pdf.txt'
        subprocess.call(['pdftotext', '-l', '1', self.path, txt],
                        shell=False, stderr=subprocess.PIPE)
        if sys.version_info[0] < 3:
            pdf_txt = codecs.open(txt, 'r', 'utf-8').readlines()
        else:
            pdf_txt = open(txt, 'r').readlines()
        os.remove(txt)
        # First search for DOI and ABS/arXiv bibcode by regex
        bibcode = None
        for line in pdf_txt:
            line = line.lower()
            try:
                self.identifier_type = 'doi'
                self.identifier = re.search(
                                    r'[0-9]{2}'       # 2 digits
                                    r'\.'             # .
                                    r'[0-9]{4}'       # 4 digits
                                    r'/'              # /
                                    r'.*?'            # min num of anything
                                    r'(?=[\ (\n)])',  # end at space/newline
                                    line            ).group()
                return
            except AttributeError:
                pass
            try:
                #arxiv bibcode
                bibcode = line.index('arxiv')
                if line[bibcode + 5] == ')':
                    continue
                bibcode = line.split()[0][6:]
                if bibcode[-2] == 'v':
                    bibcode = bibcode[:-2]
                self.identifier_type = 'arxiv'
                self.identifier = bibcode
                return
            except ValueError:
                pass
            try:
                #abs bibcode
                self.identifier_type = 'abs'
                self.identifier = re.match(
                                    r'[0-9]{4}'     # year
                                    r'[a-z&]{2,6}'  # journal
                                    r'.*'           # some number of .'s
                                    r'[0-9]{1,4}'   # volume
                                    r'[a-z]?'       # can have 'L' etc
                                    r'.*'           # some number of .'s
                                    r'[0-9]{1,4}'   # start page
                                    r'[a-z]'        # author initial
                                    r'\n',          # new line
                                    line          ).group()[:-1]
                return
            except AttributeError:
                continue
        pdf_txt.seek(0)
        # Not found, so have to construct an ABS bibcode
        # List so that order is preserved (for apjs)
        journals = [['a&a', 'aap'],
                    ['the astronomical journal', 'aj'],
                    ['the astrophysical journal', 'apj'],
                    ['the astrophysical journal supplement', 'apjs'],
                    ['annu. rev. astron. astrophys.', 'ara&a'],
                    ['annu. rev. astro. astrophys.', 'ara&a'],
                    ['mon. not. r. astron. soc.', 'mnras'],
                   ]
        for line in pdf_txt:
            line = line.lower()
            # Look for a single line with a journal name and year
            if (any(j[0] in line for j in journals) and
                    re.search('[0-9]{4}', line)):
                # Journal
                journal = [j[1] for j in journals if j[0] in line][-1]
                # Volume and first page
                vol_pages_re = (r'[0-9]{1,4}'     # volume
                                r'[:,\s]{1,4}'    # volume-pages separator
                                r'l?'             # if a Letter
                                r'[0-9]{1,4}'     # start page
                                r'([-––è]|\sy)?'  # start-end page separator
                                r'l?'             # if a letter
                                r'([0-9]{1,4})?'  # end page (may not exist)
                               )
                vol_pages = re.search(vol_pages_re, line).group()
                volume = re.search(r'[0-9]{1,4}[:,\s]', vol_pages).group()[:-1]
                pages = re.sub(volume, '', vol_pages)
                qualifier = '.'
                if re.search('l', pages):
                    qualifier = 'l'
                page = re.search(r'[0-9]{1,4}', pages).group()

                # Year
                year_line = re.sub([j[1] for j in journals if j[0] in line][0],
                                   '', line)
                year_line = re.sub(vol_pages, '', year_line)
                year = re.search('[0-9]{4}', year_line).group()

                # Construct bibcode from parts derived above
                self.identifier_type = 'abs'
                self.identifier = ''.join([year, journal,
                                           '.' * (9 - len(journal)
                                                    - len(volume) ),
                                           volume, qualifier,
                                           '.' * (4 - len(page)), page])
                return

    def bibtex_url(self, ads_mirror):
        """
        Get a URL of a BibTeX entry for the paper

        Parameters:
        -----------
        identifier: 2 element tuple, (identifier type, value)
            identifier type can be {'doi', arxiv', 'abs'}

        Returns:
        --------
        string
            A URL that can be resolved to find a BibTeX entry
        """
        if self.identifier_type is 'doi':
            url = ''.join(['http://', ads_mirror, '/cgi-bin/nph-bib_query?',
                           '&doi={0}'.format(self.identifier),
                           '&data_type=BIBTEX&db_key=AST&nocookieset=1'     ])
        elif self.identifier_type is 'arxiv':
            # Two different formats for arxiv_ids (change at 2007)
            # Paper may also have been submitted to another branch e.g. hep
            arxiv_ads = None
            try:  # old
                year = int(self.identifier[self.identifier.index('/') + 1:
                                           self.identifier.index('/') + 3 ])
                arxiv_ads = ''.join(['astro.ph',
                    '.' * (6 - len(str(int(self.identifier[11:])))),
                                     str(int(self.identifier[11:])) ])
            except ValueError:  # new
                year = int(self.identifier[:2])
                arxiv_ads = 'arxiv' + self.identifier
            if year > 13:
                year = str(year + 1900)
            else:
                year = str(year + 2000)
            arxiv_ads = year + arxiv_ads
            if self.identifier == 'hep':
               arxiv_ads = self.identifier
            url = ''.join(['http://', ads_mirror, '/cgi-bin/nph-bib_query?',
                           '&bibcode={0}'.format(arxiv_ads),
                           '&data_type=BIBTEX&db_key=AST&nocookieset=1'     ])
        else:  # ABS code
            url = ''.join(['http://', ads_mirror, '/cgi-bin/nph-bib_query?',
                           '&bibcode={0}'.format(quote(self.identifier)),
                           '&data_type=BIBTEX&db_key=AST&nocookieset=1'     ])
        return url

    def get_from_bibtex(self, ads_mirror):
        full_bibtex_page = req.urlopen(self.url).readlines()

        bib = []
        for line in full_bibtex_page[5:-1]:
            bib.append(line.decode('iso-8859-1'))

        bibtex_dict = parse_bibtex_entry(bib)
        self.title     = bibtex_dict['title']
        self.authors   = bibtex_dict['author']
        self.author    = bibtex_dict['author'][0][0]
        self.year      = bibtex_dict['year']
        self.reference = bibtex_dict['reference']
        self.doi       = bibtex_dict['doi']
        self.url       = bibtex_dict['adsurl'].replace(ads_mirror,
                                                       'adsabs.harvard.edu')
        self.journal   = format_journal(bibtex_dict['journal'])



def parse_bibtex_entry(bib_list):

    bib_dict = {}
    last_key = None
    for line in bib_list:
        line_list = line.split()
        try:
            if line_list[1] == '=':
                bib_dict[line_list[0]] = ' '.join(line_list[2:])
                last_key = line_list[0]
            else:
                bib_dict[last_key] += line
        except IndexError:
            if line.strip()[0] == '@':
                # Determine bibtex entry definition line properties
                bib_dict['type'] = re.search(r'(?<=@)'   # preceded by @
                                             r'.*'       # matches anything
                                             r'(?={)' ,  # followed by {
                                             line      ).group().lower()
                bib_dict['reference'] = re.search(r'(?<={)'  # preceded by {
                                                  r'.*'      # matches anything
                                                  r'(?=,)' ,  # followed by ,
                                                  line      ).group()

            continue
    # All bibtex keys are now dictionary keys
    # Need to remove { " , from beginning/end of bib_dict values
    for key in bib_dict:
        bib_dict[key] = bib_dict[key].strip()
        if bib_dict[key][-1] == ',':
            bib_dict[key] = bib_dict[key][:-1]
        while True:
            if (bib_dict[key][0] in ('{', '"')
                    and bib_dict[key][-1] in ('}', '"')):
                bib_dict[key] = bib_dict[key][1:-1]
            else:
                break

    # Now parse authors into a tuple of tuples
    authors = []
    for author in bib_dict['author'].split('and'):
        if author == '\n':
            continue
        count = 0
        name = ['']
        initials = ''
        for character in author:
            if character == '{':
                count += 1
            elif character == '}':
                count -= 1
            if count > 0 and character != '{':
                name[0] += character
            else:
                initials += character
        name[0] = latex_to_text(name[0])
        for element in initials.split('.'):
            for character in element:
                if character.isalpha():
                    name.append(character)
        authors.append(tuple(name))
    bib_dict['author'] = tuple(authors)

    return bib_dict



def exists_in_bib(pdf, bib_file):
    """
    Determine if a paper has already been added to the bib_file

    Parameters:
    -----------
    pdf: string
        The current pdf being processed
    bib_file: string
        The name of the .bib file the script writes to

    Returns:
    --------
    boolean
        True if paper exists in bib_file, False otherwise
    """
    try:
        pdf = pdf[(pdf.index('/') + 1):]
    except ValueError:
        pass
    try:
        bibcode = pdf.split()[2]
        #name_end = pdf.index(' - ')
        #ref_name = ''.join((pdf[:name_end] +
        #                    pdf[(name_end + 3):][:(pdf[(name_end + 3):] \
        #                                           .index(' - '))]
        #                   ).lower().split())
        exists = False
        with open(bib_file, 'r') as bib:  # make sure bib_file gets closed
            for line in bib:
                if line.find(bibcode) != -1:
                    exists = True
                    break
        if exists:
            return True
    except (ValueError, IOError):
        pass
    return False


def format_journal(journal):
    """
    Convert ADS journal codes into names suitable for use in references

    Parameters
    ----------
    journal: string
        An ADS BibTeX journal code eg '\apj'

    Returns
    -------
    string
        The formatted version of a journal name eg 'ApJ'
    """
    journals = {
        r'\aap': r'A\&A',
        r'\aaps': r'A\&AS',
        r'\aj': 'AJ',
        r'\apj': 'ApJ',
        r'\apjl': 'ApJL',
        r'\apjs': 'ApJS',
        r'\araa': r'ARA\&A',
        'ArXiv e-prints': 'arXiv',
        r'\mnras': 'MNRAS',
        r'\nat': 'Nature',
        r'\pasp': 'PASP',
        r'\physrep': 'Phys. Rep.',
    }
    text_name = journal
    if journal in journals:
        text_name = journals[journal]
    return text_name


def latex_to_text(latex):
    """
    Convert a string with latex characters to a standard character set

    Parameters
    ----------
    latex : string
        A string containing possible LaTeX encodings eg 'H$_{2}$O'

    Returns
    -------
    string
        A string converted to a standard format eg H20
    """
    # Set out a list of conversions (list preserves order - needed for \ etc)
    conversions = [[[r'\ss'], 'ß'],
                   [[r'\times'], '✕'],
                   [[r'\alpha'], 'α'],
                   [[r'\beta'], 'β'],
                   [[r'\mu'], 'μ'],
                   [[r'\gt'], '>'],
                   [[r'\lt'], '<'],
                   [[r'\~{n}', r'\~n'], 'ñ'],
                   [[r'\~', r'\tilde'], '~'],
                   [[r'\ndash'], '-'],
                   [[r'\&'], '&'],
                   [[r'\"', r"\'", "'", '`',
                     '{', '}','$', '/', '^', '_', '\\'], '']
                  ]
    for conversion in conversions:
        for key in conversion[0]:
            latex = latex.replace(key, conversion[1])
    return latex


def main():
    ivison = Article('./1206.pdf')
    print("repr =", repr(ivison))


if __name__ == '__main__':
    main()