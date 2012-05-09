abbrvnatR.bst and pdftobib
==========================

abbrvnatR.bst
-------------
A customised version of the natbib style abbrvnat.bst.

The differences are:
1. Authors have surnames first
2. Titles are not shown
3. Journal links to DOI
4. Volume, pages link to ADS
5. A limit of 3 authors is shown, first author + et al. is shown if more

pdftobib
--------
pdftobib is a python script that parses a given directory of PDF files
(typically journal articles) and produces a file (default library.bib)
containing bibtex entries for all possible PDF files.

This is specifically targeted at astrophysics papers.
'doi' and 'url' fields are returned with each bibtex entry, allowing for
hyperlinking using abbrvnatR.bst.

Placed in the PATH, usage is:
pdftobib [directory (default: .)] [--bibtex_file FILE (default: articles.bib)]

