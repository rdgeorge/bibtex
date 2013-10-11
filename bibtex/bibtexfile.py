import os

from bibtex.article import Article

class BibtexFile:

    def __init__(self, path=None):
        """
        Constructor, optionally imports from a specified bibtex file

        Parameters
        ----------
        path : string, optional
            The path to a bibtex file to import (default: None = self.path)
        """
        self.path = path
        self.articles = []  # List of Articles
        if os.path.isfile(str(path)):
            self.import_articles_from_file()

    def __contains__(self, item):
        """
        Returns item (a reference) in the list of article references in self
        """
        return repr(item) in [repr(article.reference)
                              for article in self.articles]


    def append(self, item):
        """
        Append an Article to the BibtexFile

        Parameters
        ----------
        item : Article
            The Article to append
        """
        if type(item) is Article:
            self.articles.append(item)
        else:
            raise TypeError


    def get(self, reference):
        """
        """
        references = [repr(article.reference) for article in self.articles]
        return self.articles[references.index(repr(reference))]



    def import_articles_from_file(self, path=None):
        """
        Import a bibtex file and create an Article for each entry

        Parameters
        ----------
        path : string, optional
            The path to a bibtex file to import (default: None = self.path)
        """
        if path is None:
            path = self.path
        # Get all lines from file
        with open(path, 'r') as bib_file:
            lines = bib_file.readlines()
        count = 0
        bibtex = []
        new_article = False
        for line in lines:
            # Find lines to use for single entry
            for character in line.strip():
                if character == '{':
                    new_article = True
                    count += 1
                elif character == '}':
                    count -= 1
            # Add line to this entry
            if line != '\n':
                bibtex.append(line)
            # Entry over, construct Article and append to self.articles
            if count < 1 and new_article:
                self.articles.append(Article(bibtex=bibtex))
                bibtex = []
                new_article = False


    def write_to_file(self, path=None):
        """
        Write a bibtex entry for all Articles to the file
        """
        # Sort by author, year
        self.articles.sort(key=lambda article: (article.author, article.year))
        if path:
            self.path = path
        with open(self.path, 'w') as bib_file:
            for article in self.articles:
                # Write first line of bibtex (@article{reference, etc)
                bib_file.write('@{0}{{{1},\n'.format(article.type,
                                                     article.reference))
                # Author list needs some special formatting
                authors = []
                for author in article.authors:
                    formatted_author = ['{', author[0], '}']
                    try:
                        formatted_author += [', ', author[1], '.']
                        for initial in author[2:]:
                            formatted_author += ['~', initial, '.']
                    except IndexError:
                        pass
                    authors.append(''.join(formatted_author))
                bib_file.write('author = {' + ' and '.join(authors) + '},\n')

                # Write other keys
                for key in article.bibtex:
                    if key != 'author':
                        bib_file.write(''.join([key, ' = {',
                                                article.bibtex[key], '},\n']))
                bib_file.write('}\n\n')
