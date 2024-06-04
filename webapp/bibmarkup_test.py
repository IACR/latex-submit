import json
from pathlib import Path
import pytest
from .bibmarkup import mark_bibtex, bibtex_to_html, BibTeXParser, BIBCITE_PATT, BIBLATEX_PATT, get_citation_map
from .metadata.compilation import CompileStatus, Compilation, PubType
import datetime
import re
from bibtexparser.model import DuplicateBlockKeyBlock

def _get_compilation(bibstr):
    data = {'paperid': 'abcdefg',
            'status': CompileStatus.COMPILING,
            'email': 'foo@example.com',
            'venue': 'eurocrypt',
            'submitted': '2023-01-02 01:02:03',
            'accepted': '2023-01-03 01:02:55',
            'pubtype': PubType.RESEARCH.name,
            'compiled': datetime.datetime.now(),
            'command': 'dummy command',
            'error_log': [],
            'warning_log': [],
            'bibtex': bibstr,
            'zipfilename': 'submit.zip'}
    return Compilation(**data)

def test_markup():
    bibtex = r"""
@article{firstkey,
  title = {This is a title},
  year = 2024,
  booktitle = @crypto2024,
}

@InProceedings{inproc:key,
  title = {The paper title},
}

@manual{oneline title={This is the title} year=2024}

@book{onebook
title="This is the title"
year=1842
}

@misc{ patashnik-bibtexing,
       author = "Oren Patashnik",
       title = "BIBTEXing",
       year = "1988" }

@phdthesis{DBLP:phd/dnb/Fitzi03,
author =        {Matthias Fitzi},
  school =        {{ETH} Zurich, Z{\"{u}}rich, Switzerland},
  title =         {Generalized communication and security models in
                   {Byzantine} agreement},
  year =          {2003},
  biburl =        {https://dblp.org/rec/phd/dnb/Fitzi03.bib},
  bibsource =     {dblp computer science bibliography, https://dblp.org},
  isbn =          {978-3-89649-853-3},
  timestamp =     {Wed, 07 Dec 2016 14:16:47 +0100},
  url =           {http://d-nb.info/967397375},
}

@inproceedings{FOCS:Yao82b,
  author =        {Andrew Chi-Chih Yao},
  booktitle =     {23rd FOCS},
  pages =         {160--164},
  publisher =     {{IEEE} Computer Society Press},
  title =         {Protocols for Secure Computations (Extended
                   Abstract)},
  year =          {1982},
}

"""
    marked = mark_bibtex(bibtex)
    assert '<span id="bibtex:firstkey">@article{firstkey,</span>' in marked
    assert '<span id="bibtex:inproc:key">@InProceedings{inproc:key,</span>' in marked
    # The comma is optional after the key. Who knew?
    assert """<span id="bibtex:oneline">@manual{oneline,</span>
title=""" in marked
    # Notice that we insert a comma when none exists.
    assert """<span id="bibtex:onebook">@book{onebook,</span>
title="This is the title"
""" in marked
    assert '<span id="bibtex:patashnik-bibtexing">@misc{patashnik-bibtexing,</span>' in marked
    assert '<span id="bibtex:DBLP:phd/dnb/Fitzi03">@phdthesis{DBLP:phd/dnb/Fitzi03,</span>' in marked
    assert '<span id="bibtex:FOCS:Yao82b">@inproceedings{FOCS:Yao82b,</span>' in marked

def test_markup_file():
    bibfile = Path('testdata/test.bib')
    bibstr = bibfile.read_text(encoding='UTF-8')
    marked = mark_bibtex(bibstr)
    print(marked)
    entries = marked.count('@')
    assert entries == 86
    assert entries == bibstr.count('@')
    assert marked.count('<span') == entries

def test_parse():
    bibfile = Path('testdata/test.bib')
    bibstr = bibfile.read_text(encoding='UTF-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    print(parser.errors)
    assert len(parser.errors) == 0
    assert len(parser.warnings) == 0
    assert len(db.entries) == 86
    bibfile = Path('testdata/bibtex/references.bib')
    bibstr = bibfile.read_text(encoding='UTF-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    print(parser.errors)
    assert len(parser.errors) == 0
    for warning in parser.warnings:
        print(warning)
    assert len(parser.warnings) == 0
    assert len(db.entries) == 86

def test_bibliography():
    bibfile = Path('testdata/bibtex/bibliography.bib')
    bibstr = bibfile.read_text(encoding='utf-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    assert len(db.entries) == 38
    assert len(parser.errors) == 0
    assert len(parser.warnings) == 0

def test_dana_bib():
    bibfile = Path('testdata/bibtex/dana_bib.bib')
    bibstr = bibfile.read_text(encoding='utf-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    assert len(db.entries) == 20
    assert len(parser.errors) == 0
    assert len(parser.warnings) == 0

def test_duplicate():
    output_dir = Path('testdata/bibtex/duplicate/')
    bibfile = output_dir / Path('the.bib')
    bibstr = bibfile.read_text(encoding='utf-8')
    cite_map = get_citation_map(output_dir)
    parser = BibTeXParser(cite_map)
    db = parser.parse_bibtex(bibstr)
    for block in db.blocks:
        print(block)
    assert len(db.entries) == 3
    assert len(db.blocks) == 5
    assert isinstance(db.blocks[4], DuplicateBlockKeyBlock)
    entry = db.entries[0]
    assert entry.entry_type == 'misc'
    fields = entry.fields_dict
    assert fields['title'].value == 'What happens to this title?'
    assert 'Title' not in fields
    assert 'author' in fields
    assert len(parser.errors) == 0
    assert len(parser.warnings) == 1
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': bibstr,
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    bibtex_to_html(compilation, cite_map)
    assert len(compilation.error_log) == 0
    assert len(compilation.warning_log) == 1
    assert compilation.warning_log[0].text == 'Duplicate bibtex entry: @misc{another,'
    
def test_cryptobib():
    output_path = Path('testdata/bibtex/cryptobib/')
    bibfile = output_path / Path('bibexport.bib')
    bibstr = bibfile.read_text(encoding='UTF-8')
    cite_map = get_citation_map(output_path)
    assert len(cite_map) == 9020
    parser = BibTeXParser(cite_map)
    db = parser.parse_bibtex(bibstr)
    assert len(db.entries) == 9020
    assert len(db.blocks) == 9020
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': bibstr,
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    bibtex_to_html(compilation, cite_map)
    count = sum([1 for warning in compilation.warning_log if 'should probably have a doi or url field.' in warning.text])
    assert count == len(compilation.warning_log)
    count = sum([1 for warning in compilation.warning_log if 'should have author field' in warning.text])
    assert count == 0
    assert len(compilation.warning_log) == 1552
    for i in range(len(compilation.error_log)):
        error = compilation.error_log[i]
        print(i, error.text)
    assert 'Rivain12 (Differential Fault Analysis of DES) requires booktitle field' in compilation.error_log[0].text
    assert 'HanSchTuy10 (Hardware Intrinsic Security from Physically Unclonable Functions) requires booktitle field' in compilation.error_log[1].text
    assert 'AMSST10 (Memory Leakage-Resilient Encryption Based on Physically Unclonable Functions) requires booktitle field' in compilation.error_log[2].text
    assert 'Kirovski10 (Anti-counterfeiting: Mixing the Physical and the Digital World) requires booktitle field' in compilation.error_log[3].text
    assert 'UllVog10 (Contactless Security Token Enhanced Security by Using New Hardware Features in Cryptographic-Based Security Mechanisms) requires booktitle field' in compilation.error_log[4].text
    assert 'JKSS10 (Efficient Secure Two-Party Computation with Untrusted Hardware Tokens (Full Version)) requires booktitle field' in compilation.error_log[5].text
    assert 'Regev10 (On the Complexity of Lattice Problems with Polynomial Approximation Factors) requires booktitle field' in compilation.error_log[6].text
    assert len(compilation.error_log) == 7

    
def test_html():
    output_dir = Path('testdata/bibtex/output2')
    bibtex_path = output_dir / Path('extracted.bib')
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': bibtex_path.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    mapping = get_citation_map(output_dir)
    bibtex_to_html(compilation, mapping)
    print(compilation.warning_log)
    assert len(compilation.warning_log) == 2
    assert len(compilation.bibhtml) == 33
    

def test_output1():
    """This is a tricky biblatex test because there is one reference
    with no alpha label, plus two that have the same labelalpha and 
    are distinguished only by extraalpha."""
    output_dir = Path('testdata/bibtex/output1')
    mapping = get_citation_map(output_dir)
    print(json.dumps(mapping, indent=2))
    assert len(mapping) == 32
    assert mapping['hyperledger'] == ''
    assert mapping['10.1007/978-3-031-15979-4_4'] == 'Alb+22'
    assert mapping['EPRINT:CamDriLeh16'] == 'CDL16a'
    assert mapping['TRUST:CamDriLeh16'] == 'CDL16b'

def test_output2():
    """This one uses bibtex instead of biblatex."""
    output_dir = Path('testdata/bibtex/output2')
    mapping = get_citation_map(output_dir)
    assert len(mapping) == 33
    assert mapping['C:CGGJK21'] == 'CGG<sup>+</sup>21'

def test_output3():
    output_dir = Path('testdata/bibtex/output3')
    cite_map = get_citation_map(output_dir)
    assert len(cite_map) == 50
    bibtex_file = output_dir / Path('bibexport.bib')
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': bibtex_file.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    bibtex_to_html(compilation, cite_map)
    # print(compilation.model_dump_json(indent=2))
    for error in compilation.error_log:
        print(error)
    assert len(compilation.error_log) == 0
    assert len(compilation.warning_log) == 0
    for warning in compilation.warning_log:
        print(warning)
    assert len(compilation.bibhtml) == 50

def test_output4():
    output_dir = Path('testdata/bibtex/output4')
    cite_map = get_citation_map(output_dir)
    assert len(cite_map) == 525
    bibtex_file = output_dir / Path('duplicate.bib')
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': bibtex_file.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    bibtex_to_html(compilation, cite_map)
    # print(compilation.model_dump_json(indent=2))
    for error in compilation.error_log:
        print(error)
    assert len(compilation.error_log) == 4
    assert 'requires title field' in compilation.error_log[0].text
    assert 'should have one of booktitle/series fields' in compilation.error_log[1].text
    assert 'should have one of year/date fields' in compilation.error_log[2].text
    assert 'should have one of year/date fields' in compilation.error_log[3].text
    # for warning in compilation.warning_log:
    #     if 'should probably have a doi or url field.' not in warning.text:
    #         print('warning=', warning)
    notdoi = [w for w in compilation.warning_log if 'should probably have a doi or url field.' not in w.text]
    assert len(notdoi) == 2
    assert notdoi[0].text == 'Duplicate bibtex entry: @inproceedings{pcf,'
    assert notdoi[1].text == 'Bibtex error: logstar: booktitle is expected for @article'
    assert len(compilation.warning_log) == 403
    assert len(compilation.bibhtml) == 525

def test_missing():
    output_dir = Path('testdata/bibtex/missing')
    cite_map = get_citation_map(output_dir)
    assert len(cite_map) == 58
    bibtex_file = output_dir / Path('missing.bib')
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': bibtex_file.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    bibtex_to_html(compilation, cite_map)
    assert len(compilation.bibhtml) == 58
    assert len(compilation.warning_log) == 2
    for i in range(len(compilation.error_log)):
        error = compilation.error_log[i]
        print(i, error)
    assert 'should have one of year/date fields' in compilation.error_log[0].text
    assert 'requires title field' in compilation.error_log[1].text
    assert 'requires author field' in compilation.error_log[2].text
    assert 'of type article should have one of journaltitle/journal fields' in compilation.error_log[5].text
    assert 'of type manual should have one of year/date fields' in compilation.error_log[17].text
    assert 'of type techreport should have one of year/date fields' in compilation.error_log[21].text
    assert 'requires title field' in compilation.error_log[6].text
    for html in compilation.bibhtml:
        print(html.label, html.body)
    assert 'text-danger' in compilation.bibhtml[0].body
    assert len(compilation.error_log) == 23 # lots of errors!

def _bstrip(txt):
    """Strip outer div on bibhtml body."""
    txt = re.sub(r'<div id="[^"]+" class="bibitem">', '', txt)
    return re.sub(r'</div>$', '', txt)

def test_bibtex_style():
    test_dir = Path('testdata/bibtex/style')
    cite_map = get_citation_map(test_dir)
    assert len(cite_map) == 25
    bibtex_file = test_dir / Path('alltypes.bib')
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': bibtex_file.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    bibtex_to_html(compilation, cite_map)
    for i, bibhtml in enumerate(compilation.bibhtml):
        print(i, _bstrip(bibhtml.body))
    assert len(compilation.bibhtml) == 25
    assert len(compilation.warning_log) == 4
    assert _bstrip(compilation.bibhtml[0].body) == 'Thomas E. Anderson, Michael Dahlin, Jeanna M. Neefe, David A. Patterson, Drew S. Roselli, and Randolph Wang.  Serverless Network File Systems.  <em>ACM Transactions on Computer Systems</em>, 14(1):41–79, 1996.'
    assert _bstrip(compilation.bibhtml[1].body) == 'Saikrishna Badrinarayanan, Aayush Jain, Nathan Manohar, and Amit Sahai.  Secure MPC: Laziness Leads to GOD. In Shiho Moriai and Huaxiong Wang, editors, <em>Advances in Cryptology – ASIACRYPT 2020, Part III</em>, volume 12493 of <em>Lecture Notes in Computer Science</em>, pages 120–150, Daejeon, South Korea. 2020.  Springer, Heidelberg, Germany.  DOI: <a href="https://doi.org/10.1007/978-3-030-64840-4_5">10.1007/978-3-030-64840-4_5</a>'
    assert _bstrip(compilation.bibhtml[2].body) == 'Tim Dierks and Christopher Allen. <em>RFC 2246 - The TLS Protocol Version 1.0</em>. Internet Activities Board, January 1999.'
    assert _bstrip(compilation.bibhtml[3].body) == 'Ivan Damgård, Daniel Escudero, and Antigoni Polychroniadou.  Phoenix: Secure Computation in an Unstable Network with Dropouts and Comebacks.  <a href="https://eprint.iacr.org/2021/1376">https://eprint.iacr.org/2021/1376</a>. Cryptology ePrint Archive, Report 2021/1376. 2021.'
    assert _bstrip(compilation.bibhtml[4].body) == 'John Doe.  The Importance of Unpublished Sources.  Personal Correspondence. 2022.'
    assert _bstrip(compilation.bibhtml[5].body) == 'Jintai Ding and Dieter Schmidt.  Solving Degree and Degree of Regularity for Polynomial Systems over a Finite Fields. In <em>Number Theory and Cryptography: Papers in Honor of Johannes Buchmann on the Occasion of His 60th Birthday</em>, pages 34–49. Springer, Berlin, Heidelberg 2013. DOI: <a href="https://doi.org/10.1007/978-3-642-42001-6_4">10.1007/978-3-642-42001-6_4</a>'
    assert _bstrip(compilation.bibhtml[6].body) == 'Whitfield Diffie, Paul C. van Oorschot, and Michael J. Wiener.  Authentication and Authenticated Key Exchanges.  <em>Designs, Codes and Cryptography</em>, 2(2):107–125, June 1992.'
    assert _bstrip(compilation.bibhtml[7].body) == 'Danny Dolev and Andrew Chi-Chih Yao.  On the Security of Public Key Protocols (Extended Abstract). In <em>22nd Annual Symposium on Foundations of Computer Science</em>, pages 350–357, Nashville, TN, USA. 1981.  IEEE Computer Society Press.  DOI: <a href="https://doi.org/10.1109/SFCS.1981.32">10.1109/SFCS.1981.32</a>'
    assert _bstrip(compilation.bibhtml[8].body) == 'Oded Goldreich.  <em>Foundations of Cryptography: Basic Applications</em>, volume 2. Cambridge University Press, Cambridge, UK 2004.'
    assert _bstrip(compilation.bibhtml[9].body) == 'Neil Haller, Craig Metz, Philip J. Nesser II, and Mike Straw. <em>RFC 2289: A One-Time Password System</em>. Internet Activities Board, February 1998.'
    assert _bstrip(compilation.bibhtml[10].body) == 'D. Kohel.  <em>Endomorphism rings of elliptic curves over finite fields</em>. PhD thesis, University of California at Berkeley, 1996.'
    assert _bstrip(compilation.bibhtml[11].body) == 'D. Lewin.  <em>Consistent hashing and random trees: Algorithms for caching in distributed networks</em>. Master\'s thesis, MIT, 1998.'
    assert _bstrip(compilation.bibhtml[12].body) == 'Ueli M. Maurer.  Secure multi-party computation made simple.  <em>Discrete Applied Mathematics</em>, 154(2):370–381, 2006. Full version at <a href="https://crypto.ethz.ch/publications/files/Maurer02b.pdf">https://crypto.ethz.ch/publications/files/Maurer02b.pdf</a> DOI: <a href="https://doi.org/10.1016/j.dam.2005.03.020">10.1016/j.dam.2005.03.020</a>'
    assert _bstrip(compilation.bibhtml[13].body) == 'Kevin S McCurley.  Odds and ends from cryptology and computational number theory. In Carl Pomerance, editor, <em>Cryptology and Computational Number Theory</em>, volume 42 of <em>Proceedings of Symposia in Applied Mathematics</em>, pages 49–74. American Mathematical Society 1990.'
    assert _bstrip(compilation.bibhtml[14].body) == 'K. Muralidhar and M. M. Sundareshan.  On the Decomposition of Large Communication Networks for Hierarchical Control Implementation.  <em>IEEE Transactions on Communications</em>, COM-34, 10:985–987, October 1986.'
    assert _bstrip(compilation.bibhtml[15].body) == 'Alfred J. Menezes, Paul C. van Oorschot, and Scott A. Vanstone.  <em>Handbook of Applied Cryptography</em>. The CRC Press series on discrete mathematics and its applications. CRC Press, 2000 N.W. Corporate Blvd., Boca Raton, FL 33431-9868, USA 1997.'
    assert _bstrip(compilation.bibhtml[16].body) == 'Ozgun Ozerk, Can Elgezen, Ahmet Can Mert, Erdinc Ozturk, and Erkay Savas.  <a href="https://eprint.iacr.org/2021/124">Efficient Number Theoretic Transform Implementation on GPU for Homomorphic Encryption</a>. Cryptology ePrint Archive, Report 2021/124. February 2021.'
    assert _bstrip(compilation.bibhtml[17].body) == 'Oded Regev.  On Lattices, Learning with Errors, Random Linear Codes, and Cryptography.  <em>J. ACM</em>, 56(6), 2009.'
    assert _bstrip(compilation.bibhtml[18].body) == 'Peter Schwabe, Roberto Avanzi, Joppe Bos, Léo Ducas, Eike Kiltz, Tancrède Lepoint, Vadim Lyubashevsky, John M. Schanck, Gregor Seiler, Damien Stehlé, and Jintai Ding.  CRYSTALS-KYBER. Technical report, National Institute of Standards and Technology.  available at <a href="https://csrc.nist.gov/Projects/post-quantum-cryptography/selected-algorithms-2022">https://csrc.nist.gov/Projects/post-quantum-cryptography/selected-algorithms-2022</a>. 2022.'
    assert _bstrip(compilation.bibhtml[19].body) == 'John Smythe and Jane Doer.  The Effects of Hemlength Change. In Bob Johnson, editor, <em>Proceedings of the Annual Conference on Climate Change</em>, pages 55–62, Los Angeles, CA. June 2022.  Springer.  This is a sample entry for a paper in conference proceedings.'
    assert _bstrip(compilation.bibhtml[20].body) == 'John Smith.  An incollection with a series. In Jane Doe, editor, <em>The Book of Examples</em>, volume 1 of <em>Example Book Series</em>, pages 123–130. Example Publisher, New York, NY 2022.'
    assert _bstrip(compilation.bibhtml[21].body) == 'John Smith.  An incollection without series. In Jane Doe, editor, <em>The Book of Examples</em>, pages 123–130. Example Publisher, New York, NY 2022.'
    assert _bstrip(compilation.bibhtml[22].body) == 'Anton Stolbunov.  <em>Cryptographic schemes based on isogenies</em>. PhD thesis, Norges teknisk-naturvitenskapelige universitet, Fakultet for informasjonsteknologi, matematikk og elektroteknikk, Institutt for telematikk, 2012.'
    assert _bstrip(compilation.bibhtml[23].body) == 'ZenGo.  <a href="https://github.com/ZenGo-X/white-city/blob/master/White- City-Report/whitecity_new.pdf">White-City: A Framework For Massive MPC with Partial Synchrony and Partially Authenticated Channels</a>. 2020.'
    assert _bstrip(compilation.bibhtml[24].body) == 'Fester Zester.  My life story in 25 words or less. Available at <a href="https://eprint.iacr.org/2015/939.pdf">https://eprint.iacr.org/2015/939.pdf</a>. May 2015.'
