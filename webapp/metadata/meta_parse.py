"""
Library for handling output meta file from compiling latex.
"""

from nameparser import HumanName
from arxiv_latex_cleaner import arxiv_latex_cleaner
import random
import re
import shutil
import string
import sys
import tempfile
import xml.etree.ElementTree as ET
from pylatexenc import latexwalker
from pylatexenc.latex2text import LatexNodes2Text, get_default_latex_context_db, MacroTextSpec, EnvironmentTextSpec, SpecialsTextSpec

# because of arxiv_latex_cleaner
assert sys.version_info >= (3,9)

try:
    from .compilation import CompileError, ErrorType, Compilation
except Exception as e:
    from compilation import CompileError, ErrorType, Compilation

from pathlib import Path
import os
import re
import subprocess

def get_key_val(line):
    """If line has form key: value, then return key, value."""
    colon = line.find(':')
    if colon < 0:
        raise Exception('Exception: missing colon: {}'.format(line))
    key = line[:colon].strip()
    val = line[colon+1:].strip()
    return key, val

def extract_bibtex(root_path: str, output_path: Path, compilation: Compilation):
    """This is used to populate the bibtex field of compilation.
     This implementation uses bibexport, which is only supported
     under bibtex (not biber). In order to overcome this, we create a
     temporary aux file that can be processed by bibexport. An
     alternative implementation could be built by parsing the aux
     file to extract the \bibcite entries, and then use pybtex or
     another parser to parse the bibtex files and extract the
     entries. We chose to use bibexport because it is the fastest and
     most reliable parser of bibtex.
    """
    try:
        auxfilename = 'main.aux'
        aux_file = output_path / Path('main.aux')
        if not aux_file.is_file():
            compilation.error_log.append(CompileError(error_type=ErrorType.LATEX_ERROR,
                                                      logline=0,
                                                      text='Missing aux file'))
            return
        # We use a custom "wideexport" for bibexport. It needs to be in the path for
        # bibexport to find it, so we copy it to the current output_path with a random filename
        # and remove it when we are done.
        bibtex_style_file = Path(root_path) / Path('metadata/wideexport.bst')
        bst_filename = 'bst_' + ''.join(random.choices(string.ascii_uppercase, k=10)) + '.bst'
        bst_file = output_path / Path(bst_filename)
        shutil.copy(bibtex_style_file, bst_file)
        bcf_file = output_path / Path('main.bcf')
        if bcf_file.is_file():
            # In this case the author used biblatex/biber, so we
            # create a temporary auxfile to use for bibexport.
            cite_keys = set()
            bibsources = []
            tree = ET.parse(str(bcf_file))
            root = tree.getroot()
            for child in root.iter('{https://sourceforge.net/projects/biblatex}citekey'):
                cite_keys.add(child.text)
            for child in root.iter('{https://sourceforge.net/projects/biblatex}datasource'):
                bibsources.append(child.text)
            bibsources = ','.join([a[:-4] for a in bibsources])
            auxfilename = 'tmp_' + ''.join(random.choices(string.ascii_uppercase, k=10)) + '.aux'
            aux_file = output_path / Path(auxfilename)
            cite_keys = list(cite_keys)
            tmpauxlines = ['\\citation{' + key + '}' for key in cite_keys]
            tmpauxlines.append('\\bibstyle{plain}')
            tmpauxlines.append('\\bibdata{' + bibsources + '}')
            tmpauxlines.extend(['\\bibcite{' + cite_keys[i] + '}{' + str(i) + '}' for i in range(len(cite_keys))])
            tmpauxcontents = '\n'.join(tmpauxlines) + '\n'
            aux_file.write_text(tmpauxcontents, encoding='UTF-8', errors='replace')
        with tempfile.TemporaryDirectory() as tmpdir:
            bibfile = tmpdir / Path('main.bib')
            args = ['bibexport', '-b', bst_filename, '-o', str(bibfile.resolve()), auxfilename]
            process = subprocess.run(args,
                                     cwd=output_path.resolve(),
                                     encoding='UTF-8',
                                     errors='replace',
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
            if auxfilename != 'main.aux':
                aux_file.unlink()
            if process.returncode:
                compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                          logline=0,
                                                          text='Error in bibexport {}:{}'.format(process.returncode,
                                                                                                 process.stdout)))
            if bibfile.is_file():
                compilation.bibtex = bibfile.read_text(encoding='UTF-8', errors='replace')
            else:
                compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                          logline=0,
                                                          text='No output from bibexport: {}'.format(process.stdout)))
    except Exception as e:
        compilation.error_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                  logline=0,
                                                  text='Error checking in extract_bibtex: {}. This may be a bug'.format(str(e))))
    finally:
        bst_file.unlink()



def illegal_handler(n):
    """output <span> to show that conversion failed."""
    if n.isNodeType(latexwalker.LatexMacroNode):
        return "<span class='text-danger'>Illegal macro in textabstract: '\\{}'</span>".format(n.macroname)
    elif n.isNodeType(latexwalker.LatexEnvironmentNode):
        return "<span class='text-danger'>Illegal environment in textabstract: '\\begin{{{}}}'</span>".format(n.environmentname)
    return "<span class='text-danger'>Illegal latex construct in textabstract: '{}'</span>".format(n.latex_verbatim())

# The code below is used for handling things like \begin{enumerate}\item first\item second\end{enumerate}
class EnumContext:
    """Used to keep track of being in an itemize or enumerate environment."""
    def __init__(self, env=None, nest_level=0, item_no=0):
        self.env = env # the name of the environment.
        self.nest_level = nest_level # we do not support nesting of itemize or enumerate.
        self.item_no = item_no # the item number in the list (starting at 1)

def enum_environment_to_text(n, l2tobj):
    if n.environmentname not in ('enumerate', 'itemize'):
        # in particular we do not support description.
        raise RuntimeError('environment must be "itemize" or "enumerate"')
    try:
        old_context = getattr(l2tobj, 'context_enum_environment', EnumContext())
        if old_context.nest_level > 0:
            return r"<span class='text-danger'>nesting of enumerate or itemize is not allowed</span>"
        l2tobj.context_enum_environment = EnumContext(n.environmentname, old_context.nest_level+1, 0)
        if n.environmentname == 'enumerate':
            s = '</p><ol>' + l2tobj.nodelist_to_text(n.nodelist) + '</li></ol><p>'
        else:
            s = '</p><ul>' + l2tobj.nodelist_to_text(n.nodelist) + '</li></ul><p>'
    finally:
        l2tobj.context_enum_environment = old_context
    return s

def item_to_text(n, l2tobj):
    enumcontext = getattr(l2tobj, 'context_enum_environment', EnumContext())
    itemstr = ''
    enumcontext.item_no += 1
    if n.nodeoptarg:
        itemstr = l2tobj.nodelist_to_text([n.nodeoptarg])
    if enumcontext.env == 'itemize' or enumcontext.env == 'enumerate':
        if enumcontext.item_no > 1:
            itemstr += '</li>'
        itemstr += '<li>'
    else:
        itemstr = r"<span class='text-danger'>\item only allowed inside enumerate or itemize environment in textabstract.</span>"
    return itemstr

def get_converter():
    """Return a customized LatexNodes2Text for latex => text conversion. This outputs HTML to
    signifify errors for the author when they use something not covered by the converter.
    """
    lt_context_db = get_default_latex_context_db().filter_context(
        exclude_categories=['latex-placeholders'])
    lt_context_db.add_context_category('enum-context',
                                       macros=[
                                           MacroTextSpec('item', simplify_repl=item_to_text)
                                       ],
                                       environments=[
                                           EnvironmentTextSpec('enumerate', simplify_repl=enum_environment_to_text),
                                           EnvironmentTextSpec('itemize', simplify_repl=enum_environment_to_text),
                                       ],
                                       prepend=True)
    lt_context_db.add_context_category('stripper',
                                       macros=[MacroTextSpec('textsf', '%s'),
                                               MacroTextSpec('href', simplify_repl=illegal_handler),
                                               MacroTextSpec('input', simplify_repl=illegal_handler),
                                               MacroTextSpec('include', simplify_repl=illegal_handler),
                                               MacroTextSpec('sc', ''),
                                               MacroTextSpec('boldmath', ''),
                                               MacroTextSpec('bm', ''),
                                               MacroTextSpec('todo', simplify_repl=illegal_handler),
                                               MacroTextSpec('sl', '')],
                                       environments=[EnvironmentTextSpec('math', discard=False)],
                                       specials= [
                                           SpecialsTextSpec('&', '&'), # leave these alone since they may occur
                                           # inside character entities like &gt;
                                       ],
                                       prepend=True)
    lt_context_db.set_unknown_macro_spec(MacroTextSpec('', simplify_repl=illegal_handler))
    lt_context_db.set_unknown_environment_spec(EnvironmentTextSpec('', simplify_repl=illegal_handler))
    return LatexNodes2Text(math_mode='verbatim', latex_context=lt_context_db)

def clean_abstract(text):
    """The purpose of this method is to remove comments from the abstract
    and convert to text that is safe to use within HTML. This means
    that the mathematical operators < and > are changed to &lt; and
    &gt; Paragraphs that are signified by a blank line in LaTeX are
    replaced by </p><p>. Some LaTeX macros are changed into UTF-8, and
    the enumerate and itemize environments are converted into <ol> and
    <ul>. Raw mathematics is left intact so it can be handled by
    MathJax. If it encounters illegal macros, then it emits a <span>
    with an error message. Abstracts are converted from this format to
    XML in the get_jats_abstract method.
    """
    lines = text.splitlines(keepends=True)
    # There is some doubt about whether to include things like \textrm
    # in the commands_only_to_delete. It depends on how mathjax or
    # katex is configured.
    args = {'commands_only_to_delete': [],
            'commands_to_delete': [
                'todo',
                'footnote']}
    # This is an internal command, so we may have to change to our own code
    # or using it through subprocess.
    clean_text = arxiv_latex_cleaner._remove_comments_and_commands_to_delete(lines, args)
    # for some reason, arxiv_latex_cleaner leaves % at end of line in order
    # to preserve LaTeX spacing. We remove it unless it is \%
    clean_text = re.sub(r'[^\\]%', '', clean_text)
    clean_text = clean_text.replace('&', '&amp; ').replace('<', '&lt;').replace('>', '&gt;')
    clean_text = re.sub(r'\n\n', '</p><p>', clean_text)
    clean_text = re.sub(r'\n', ' ', clean_text) # unwrap lines.
    clean_text = '<p>' + clean_text + '</p>'
    converter = get_converter()
    clean_text = converter.latex_to_text(clean_text)
    patt = re.compile(r'<p>\s*</p>', re.MULTILINE) # remove empty paragraphs.
    return patt.sub('', clean_text.strip())

if __name__ == '__main__':
    import argparse
    argparser = argparse.ArgumentParser(description='abstract cleaner')
    argparser.add_argument('--file',
                           default = 'abstract.txt')
    args = argparser.parse_args()
    abstract = Path(args.file).read_text(encoding='UTF-8')
    print(clean_abstract(abstract))
