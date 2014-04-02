# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import os, re, subprocess, sys
from string import whitespace
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


class Article:

    def __init__(self, path=None, bibtex=None):
        """
        Constructor, takes optional path to pdf or bibtex (list of strings)

        Parameters
        ----------
        path : string, optional
            A path to a pdf to parse and retrieve bibtex from ADS
        bibtex : list of strings, optional
            A list containing a bibtex entry for an article
        """
        self.path = path
        # ADS mirror to query (to take load off adsabs.harvard.edu)
        self.ads_mirror = 'esoads.eso.org'

        # If a pdf has been given
        if path is not None:
            # Extract identifying information from the pdf
            self.identifier, self.identifier_type = \
                                             self._identifier_from_article()
            # Construct a url linking to the article bibtex entry at ADS
            self.url = self._bibtex_url()
            # Parse the bibtex entry
            self._import_from_bibtex_url()
            # Rename the file in the pattern
            # author - year - ads_bibcode - title.pdf
            self._rename_file()

        # If a list of strings containing a bibtex entry has been given
        if bibtex is not None:
            self.import_from_bibtex(bibtex)


    def __repr__(self):
        """
        Return the ads bibcode (a unique identifier of the article)
        """
        return self.reference


    def _identifier_from_article(self):
        """
        Extract identifying information from a text file converted from a pdf

        Long method with lots of regex magic

        Returns
        -------
        tuple: 2 elements, (identifier, identifier type)
            identifier type can be {'doi', arxiv', 'abs'}
        """
        # Convert the first page of the pdf to text so it can be parsed
        txt = 'pdf.txt'
        subprocess.call(['pdftotext', '-l', '1', self.path, txt],
                        shell=False, stderr=subprocess.PIPE)
        # Read the text file
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
                identifier_type = 'doi'
                identifier = re.search(r'[0-9]{2}'       # 2 digits
                                       r'\.'             # .
                                       r'[0-9]{4}'       # 4 digits
                                       r'/'              # /
                                       r'.*?'            # min num of anything
                                       r'(?=[\ (\n)])',  # end at space/newline
                                       line            ).group()
                return identifier, identifier_type
            except AttributeError:
                pass
            try:
                #arxiv bibcode
                bibcode = line.index('arxiv')
                if line[bibcode + 5] == ')':
                    continue
                if line.split()[0][:5] != 'arxiv':
                    continue
                bibcode = line.split()[0][6:]
                if bibcode[-2] == 'v':
                    bibcode = bibcode[:-2]
                identifier_type = 'arxiv'
                identifier = bibcode
                return identifier, identifier_type
            except ValueError:
                pass
            try:
                #abs bibcode
                identifier_type = 'abs'
                identifier = re.match(r'[0-9]{4}'     # year
                                      r'[a-z&]{2,6}'  # journal
                                      r'.*'           # some number of .'s
                                      r'[0-9]{1,4}'   # volume
                                      r'[a-z]?'       # can have 'L' etc
                                      r'.*'           # some number of .'s
                                      r'[0-9]{1,4}'   # start page
                                      r'[a-z]'        # author initial
                                      r'\n',          # new line
                                      line          ).group()[:-1]
                return identifier, identifier_type
            except AttributeError:
                continue

        # Not found, so have to construct an ABS bibcode
        # List so that order is preserved (for apjs)
        journals = [['a&a', 'aap'],
                    ['the astronomical journal', 'aj'],
                    ['the astrophysical journal', 'apj'],
                    ['the astrophysical journal supplement', 'apjs'],
                    ['annu. rev. astron. astrophys.', 'ara&a'],
                    ['annu. rev. astro. astrophys.', 'ara&a'],
                    ['mon. not. r. astron. soc.', 'mnras'],
                    ['pasj', 'pasj'],
                    ['res. astron. astrophys.', 'raa'],
                    ['research in astron. astrophys.', 'raa']
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
                                r'[0-9]{1,4}'     # start page s
                                r'([-––è]|\sy)?'  # start-end page sep
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
                identifier_type = 'abs'
                identifier = ''.join([year, journal,
                                           '.' * (9 - len(journal)
                                                    - len(volume) ),
                                           volume, qualifier,
                                           '.' * (4 - len(page)), page])
                return identifier, identifier_type


    def _bibtex_url(self):
        """
        Get a URL of a BibTeX entry for the paper

        Returns
        -------
        string
            A URL that can be resolved to find a BibTeX entry
        """
        if self.identifier_type is 'doi':
            url = ''.join(['http://', self.ads_mirror,
                           '/cgi-bin/nph-bib_query?',
                           '&doi={0}'.format(self.identifier),
                           '&data_type=BIBTEX&db_key=AST&nocookieset=1'     ])
        elif self.identifier_type is 'arxiv':
            # Two different formats for arxiv_ids (change at 2007)
            # Paper may also have been submitted to another branch e.g. hep
            arxiv_ads = None
            try:  # old {year}astro.ph..9601  2004hep.ph....4175
                arxiv_section = 'astro.ph'
                if self.identifier[:3] == 'hep':
                    arxiv_section = 'hep.ph'
                # Month and submission number
                arxiv_ads = str(int(self.identifier[-5:]))
                # Total length is 14 (18 with year)
                arxiv_ads = ''.join([arxiv_section,
                                     '.' * (14 - len(arxiv_section)
                                            - len(arxiv_ads)       ),
                                     arxiv_ads                       ])
                # Needs to be int for processing later
                year = int(self.identifier[self.identifier.index('/') + 1:
                                           self.identifier.index('/') + 3 ])
            except ValueError:  # new {year}arxiv{identifier}
                # self.identifier in form 1201.4773v1
                year = int(self.identifier[:2])
                arxiv_ads = 'arxiv' + self.identifier
            if year > 14:  # I don't like this
                year = str(year + 1900)
            else:
                year = str(year + 2000)
            arxiv_ads = year + arxiv_ads
            url = ''.join(['http://', self.ads_mirror,
                           '/cgi-bin/nph-bib_query?',
                           '&bibcode={0}'.format(arxiv_ads),
                           '&data_type=BIBTEX&db_key=AST&nocookieset=1'     ])
        else:  # ABS code
            url = ''.join(['http://', self.ads_mirror,
                           '/cgi-bin/nph-bib_query?',
                           '&bibcode={0}'.format(quote(self.identifier)),
                           '&data_type=BIBTEX&db_key=AST&nocookieset=1'     ])
        return url


    def _import_from_bibtex_url(self):
        """
        Get the bibtex entry for the article from ADS and parse it
        """
        # Get the entry from self.url
        full_bibtex_page = req.urlopen(self.url).readlines()

        # Get range of lines to parse
        bib = []
        for line in full_bibtex_page[5:-1]:
            bib.append(line.decode('iso-8859-1'))
        # Parse these lines
        self.import_from_bibtex(bib)


    def import_from_bibtex(self, bibtex):
        """
        Parse a bibtex entry and fill various member variables

        Parameters
        ----------
        bibtex : list of strings
            The bibtex entry to parse
        """
        # Get a dictionary of the bibtex key value pairs
        self.bibtex = _parse_bibtex_entry(bibtex)

        # Fill member variables from this dictionary
        self.author      = self.bibtex['author'][0][0]
        self.authors     = self.bibtex['author']
        try:
            self.doi     = self.bibtex['doi']
        except KeyError:  # arXiv papers may not have DOIs yet
            pass
        try:
            self.journal = self.bibtex['journal'] = \
                                _format_journal(self.bibtex['journal'])
        except KeyError:  # Some conference proceedings do not have journals
            self.journal = self.bibtex['series']
        self.reference   = self.bibtex['reference']
        try:
            self.title   = self.bibtex['title']
        except KeyError:
            self.title   = ""
        self.type        = self.bibtex['type']
        # Replace ADS mirror with main page for inclusion in bibtex file
        try:
            self.url     = self.bibtex['url'] = self.bibtex['adsurl'] = \
                            self.bibtex['adsurl'].replace(self.ads_mirror,
                                                          'adsabs.harvard.edu')
        except KeyError:
            self.url     = ""
        self.year        = self.bibtex['year']

        # These were just to fill the member variables (not wanted in bibtex)
        for key in ('reference', 'type'):
            del(self.bibtex[key])


    def _rename_file(self):
        """
        Rename the pdf following a specific pattern

        Authur - Year - ADS bibcode - Title.pdf
        """
        print(self.path)
        print(''.join(['  --> ', os.path.split(self.path)[0],
                       '/',
                       ' - '.join([_latex_to_text(self.author),
                                   self.reference,
                                   _latex_to_text(self.title)]),
                       '.pdf',
                       '\n'
                       ]))
        os.rename(self.path,
                  ''.join([os.path.split(self.path)[0],
                           '/',
                           ' - '.join([_latex_to_text(self.author),
                                       self.reference,
                                       _latex_to_text(self.title)  ]),
                           '.pdf'
                           ]))


def _parse_bibtex_entry(bib_list):
    """
    Parse the text of a bibtex entry for an article and return a dictionary

    Parameters
    ----------
    bib_list : list of strings
        The bibtex entry to parse

    Returns
    -------
    dictionary
        A dictionary of bibtex key : value pairs
    """
    bib_dict = {}
    last_key = None
    for line in bib_list:
        line_list = line.split()
        try:
            if line_list[1] == '=':  # If the start of key = value pair
                bib_dict[line_list[0]] = line_list[2:]
                last_key = line_list[0]
            else:
                raise IndexError
        except IndexError:  # If not the start of a key = value pair
            if line[0] == '@':
                # Determine bibtex entry definition line properties
                bib_dict['type'] = [
                        re.search(r'(?<=@)'  # preceded by @
                                  r'.*'      # matches anything
                                  r'(?={)',  # followed by {
                                  line
                                  ).group().lower()
                                    ]
                bib_dict['reference'] = [
                        re.search(r'(?<={)'  # preceded by {
                                  r'.*'      # matches anything
                                  r'(?=,)' ,  # followed by ,
                                  line
                                  ).group()
                                         ]
            else:
                # Add line to value of last defined key
                bib_dict[last_key] += line_list
    # Remove last } of entry
    bib_dict[last_key] = ''.join( \
                ' '.join(bib_dict[last_key]).rsplit('}', 1)).split()

    # All bibtex keys are now dictionary keys
    # Need to remove { " , from beginning/end of bib_dict values
    for key in bib_dict:
        bib_dict[key] = ' '.join(bib_dict[key])
        if bib_dict[key][-1] == ',':
            bib_dict[key] = bib_dict[key][:-1]
        while True:
            count = 0
            len_greater_than_0 = 0
            for character in bib_dict[key]:
                if count > 0:
                    len_greater_than_0 += 1
                if character == '{':
                    count += 1
                elif character == '}':
                    count -= 1
            try:
                if ((bib_dict[key][0] == '"' and bib_dict[key][-1] == '"')
                        or
                        len_greater_than_0 == (len(bib_dict[key]) - 1)    ):
                    bib_dict[key] = bib_dict[key][1:-1]
                else:
                    raise IndexError
            except IndexError:
                break

    # Now parse authors into a tuple of tuples
    # This is hardcoded for ADS braces format
    authors = []
    # Authors separated by ' and '
    # Example author: {Ivezi{\'c}}, {\v Z}.~R.
    for author in bib_dict['author'].split(' and '):
        if author == '\n':
            continue
        try:
            name = [re.search(r'(?<=\{).+(?=\},)', author).group(0)]
            initials = re.search(r'(?<=\},).*', author).group(0).split('.')
            for initial in initials:
                stripped = initial.strip('~' + whitespace)
                if stripped != '':
                    name.append(stripped)
        except AttributeError:
            try:
                name = [re.search(r'(?<=\{).+(?=\})', author).group(0)]
            except AttributeError:  # likely et al.
                name = [author]
        authors.append(tuple(name))
    bib_dict['author'] = tuple(authors)

    return bib_dict


def _format_journal(journal):
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
        r'\pasj': 'PASJ',
        r'\pasp': 'PASP',
        r'\physrep': 'Phys. Rep.',
    }
    if journal in journals:
        return journals[journal]
    return journal


def _latex_to_text(latex):
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
    # Set out a list of conversions (list preserves order - req. for \ etc)
    conversions = [[[r'\ss'], 'ß'],
                   [[r'\times'], '✕'],
                   [[r'\alpha'], 'α'],
                   [[r'\beta'], 'β'],
                   [[r'\mu'], 'μ'],
                   [[r'\gt'], '>'],
                   [[r'\lt'], '<'],
                   [[r'\~{n}', r'\~n'], 'ñ'],
                   [[r'\l'], 'ł'],
                   [[r'\o'], 'ø'],
                   [[r'\v s'], 'š'],
                   [[r'\~', r'\tilde'], '~'],
                   [[r'\ndash'], '-'],
                   [[r'\&'], '&'],
                   [[r"\'a"], 'á'],
                   [[r"\'e"], 'é'],
                   [[r'\"o'], 'ö'],
                   [[r'\"u'], 'ü'],
                   [[r'\"', r"\'", "'", '`',
                     '{', '}','$', '/', '^', '_', '\\'], '']
                  ]
    for conversion in conversions:
        for key in conversion[0]:
            latex = latex.replace(key, conversion[1])
    return latex
