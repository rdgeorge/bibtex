Astronomy latex bibliography tools
==================================

apj_style.bst
-------------
A customised version of the natbib style ``abbrvnat.bst``, replicating several
features of the ApJ bibtex style.

Usage is::

    \usepackage{natbib}
    \bibliographystyle{apj_style}

The differences are:

1. Authors have surnames first
2. Titles are not shown
3. Journal links to DOI (color: rhodamine)
4. Volume, pages link to ADS (color: blue)
5. A limit of 5 authors is shown, first author + et al. is shown if more

Linking only the year of each inline reference to the full reference in the
reference section can be acheived by adding the following to the ``.tex``
file::

    % Patch so only year is linked
    \makeatletter
    % Patch case where name and year have no delimiter
    \patchcmd{\NAT@citex}
        {\@citea\NAT@hyper@{\NAT@nmfmt{\NAT@nm}\NAT@date}}
        {\@citea\NAT@nmfmt{\NAT@nm}\NAT@hyper@{\NAT@date}}
        {}% Do nothing if patch works
        {}% Do nothing if patch fails
    % Patch case where name and year have basic delimiter
    \patchcmd{\NAT@citex}
        {\@citea\NAT@hyper@{%
             \NAT@nmfmt{\NAT@nm}%
             \hyper@natlinkbreak{\NAT@aysep\NAT@spacechar}{\@citeb\@extra@b@citeb}%
             \NAT@date}}
        {\@citea\NAT@nmfmt{\NAT@nm}%
         \NAT@aysep\NAT@spacechar%
         \NAT@hyper@{\NAT@date}}
        {}% Do nothing if patch works
        {}% Do nothing if patch fails
    % Patch case where name and year are separated by a prenote
    \patchcmd{\NAT@citex}
        {\@citea\NAT@hyper@{%
             \NAT@nmfmt{\NAT@nm}%
             \hyper@natlinkbreak
             {\NAT@spacechar\NAT@@open\if*#1*\else#1\NAT@spacechar\fi}%
             {\@citeb\@extra@b@citeb}%
             \NAT@date}}
        {\@citea\NAT@nmfmt{\NAT@nm}%
            \NAT@spacechar\NAT@@open\if*#1*\else#1\NAT@spacechar\fi%
            \NAT@hyper@{\NAT@date}}
        {}% Do nothing if patch works
        {}% Do nothing if patch fails
    \makeatother

apj_style.bbx
-------------
A customised version of the biblatex style ``biblatex-phys.bbx``, replicating
several features of the ApJ bibtex style.

Usage is::

    \usepackage[
      backend=biber,
      backref=true,
      bibstyle=apj_style,
      citestyle=authoryear-comp,
      ]{biblatex}

pdftobib
--------
A script that parses a given directory of PDF files (typically journal
articles) and produces a file (default ``articles.bib``) containing bibtex
entries for all PDF files successfully processed.

This is specifically targeted at astrophysics papers.
``doi`` and ``url`` fields are returned with each bibtex entry, allowing for
hyperlinking using ``apj_style.bst`` or ``apj_style.bbx``.

Usage is::

    pdftobib [DIRECTORY (default: .)] [--bibtex_file FILE (default: articles.bib)]

mnbib
-----
Prepares a large ``.bib`` file for submission by parsing the ``.bbl`` produced
and copying only the used entries into a new ``.bib`` file.
Also adds arXiv identifiers to an ``arxiv`` journal tag if the entry is an
arXiv preprint.

