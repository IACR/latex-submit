r"""This file contains parsers for LaTeX logs. The goal is to produce
a sequence of CompileError values from metadata/compilation.py that
allows a UI to show where the error occurred in the source file and
PDF file.

Unfortunately, parsing logs is difficult because there is no defined
structure. A package or class file or latex file can potentiallly spit
out any characters to the log, but there are some recognizable
patterns that we look for. This file is based on heuristics culled
from other sources.

One problem is that the current file being processed when a line is
written to the log can be hard to recognize.  When a file is opened it
is indicated with a left parenthesis '(' followed by the filename, and
the close is indicated by a right parenthesis. Unfortunately there are
many packages that produce patterns to confuse this, e.g.,:

Missing character: There is no ) in font nullfont!
(Font)                  OT1/cmr/m/n --> OT1/lmr/m/n on input line 22.
(babel)             (\language22). Reported on input line 108.
Package: multicol 2021/11/30 v1.9d multicolumn formatting (FMi)
(rerunfilecheck)             Checksum: 821F063252D8281B36D67050115B2DB9;517.

There are various parsers that have attempted to overcome this using
heuristics (e.g., forbid some characters like spaces from filenames,
and check that the file actually exists). We choose a different route
because we are only concerned with parsing logs produced by one document
class. Because of this more modest goal, we can use the currfile package
 and insert lines into the log that look like:

iacrcc:opened with <filename>
iacrcc:opened as <filename>

This allows us to keep track of which file produces an error.

Output lines in the log are typically wrapped at 79 characters, but
this can be changed in some LaTeX engines using texmf.cnf (we change
it to 2000 characters).  Other potential problems include the fact
that pdflatex and lualatex have different output, bibtex and biber
have different output, the files may not be in a single character
encoding, etc. This class should be regarded as a collection of
heuristics rather than a formal parser.

NOTE: some errors span multiple lines, and we would need to lookahead
to capture all of the information. These are relatively rare, but have
been seen from microtype, Fonts, and hyperref.
"""

import os
try:
    from .metadata import ErrorType, CompileError
except Exception as e:
    from metadata import ErrorType, CompileError
import logging
from pathlib import Path
import re
import sys
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.dirname(SCRIPT_DIR))


# We look for this pattern in the log file to represent
# message about which file is opened or closed.
filepatt = 'iacrcc:'

warning_re = re.compile(r"^((?:La|pdf)TeX|Package|Class)(?: (\w+))? [wW]arning:?(.+)$")
error_re = re.compile(r'^(?:! ((?:La|pdf)TeX|Package|Class)(?: (\w+))? [eE]rror(?: \(([\\]?\w+)\))?: (.*)|! (.*))')
# For some reason the LaTeX developers were not satisfied with
# \PackageWarning and \PackageError because they wanted
# internationalization. For this reason they defined additional macros
# like \msg_error and \msg_fatal for packages in latex3. They produce
# different patterns and are used by many packages like fontspec.
l3msg_re = re.compile(r'^([^:]+):([0-9]+):(?:( Critical| Fatal)? Package) (\w+) (Error|Warning)')

# regular expression to find page numbers. Since we use totpages, it sets
# \count1 equal to \count0 so that page numbers are recorded as [2.2]
# instead of just [2 but we don't bother to check this more precise pattern.
pageno_re = re.compile(r'\[(?P<num>[0-9]+)')

# 'with' means it is an absolute path. 'as' may only have the filename.
opened_file_re = re.compile('^{}(?P<action>opened|closed) (as|with) (?P<filename>[^ ]*)'.format(filepatt))

# Sometimes we look for and identify the input line number
line_re = re.compile('on input line (?P<line>[0-9]+)')

citation_re = re.compile(r"^LaTeX Warning: (Citation|Reference) `([^']+)' on page (\d+) undefined on input line (\d+)\.")

# Different groups will be populated for different kinds of errors
# There are seven groups for the following regex:
# 1: type (Over|Under)
# 2: direction (h|v)
# 3: underfull box badness \d+
# 4: overfull box over size in pt
# 5: multi-line start line
# 6: multi-line end line
# 7: single line (at line \d)
badbox_re = re.compile(r"^(Over|Under)full \\([hv])box "
                       r"\((?:badness (\d+)|(\d+(?:\.\d+)?)pt too \w+)\) (?:"
                       r"(?:(?:in paragraph|in alignment|detected) "
                       r"(?:at lines (\d+)--(\d+)|at line (\d+)))"
                       r"|(?:has occurred while [\\]output is active [\[](\d+)?[\]]))")

missing_char_re = re.compile(r'Missing character: There is no')
end_occurred_inside_re = re.compile(r'^\(\\end occurred inside a group at level')

class LatexLogParser:
    r"""Ths relies upon regular expressions to recognize five types of errors: 
    1. Things emitted by \Package(Warning|Error) or \Class(Warning|Error).
    2. (over|under)full (h|v)boxes
    3. missing references from \cite
    4. duplicate references.
    It keeps track of the current PDF page and current file being read.
    """
    
    def __init__(self, main_file='main.tex', class_file='iacrcc.cls', wrap_len=79):
        """main_file and class_file go on the stack of opened files. When the parser
           runs, it will update class_file to the correct value from the log. wrap_len
           is the length at which lines should be wrapped (79 is texlive default)."""
        self.lines = None
        self.errors = []
        self.current_page = 0
        self.wrap_len = wrap_len
        self.doc_class = None # Should be set from the log.
        # opened_files is a stack of open files. This is only valid if
        # filepatt is used as described above. Note that main_file and
        # class_file are opened before logging of currfile kicks in.
        self.main_file = main_file
        # At first I thought we should have the class file and
        # currfile.sty, but apparently neither is required.
        self.opened_files = [main_file] #, class_file] # , 'currfile.sty']

    def error_ignored(self, error):
        """We have chosen to ignore some errors as they are unhelpful.
           hyperref mostly complains about mathematics in section headings,
           but we deem these unimportant. sectsty.sty complains about
           redefinition of \\underline, but we don't use that in section
           headings.
        """
        if error.filepath and error.filepath.endswith('sectsty.sty'):
            return True
        if error.package and error.package == 'hyperref':
            return True
        return False

    def current_file(self):
        if len(self.opened_files):
            return self.opened_files[-1]
        return None
                
    def _create_error(self, error_type, line, i):
        return CompileError(error_type=error_type,
                            text=line,
                            logline=i,
                            filepath=self.current_file(),
                            pageno = self.current_page)
                             

    def parse_file(self, path, debug=False):
        """May be called only once with a pathlib Path parameter."""
        if self.lines != None:
            raise RuntimeError('parse should be called only once')
        try:
            logstr = path.read_text(encoding='UTF-8', errors='replace')
        except Exception as e:
            self.errors.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                            logline=0,
                                            text='log file is not UTF-8'))
            logstr = path.read_text(encoding='UTF-8', errors='replace')
        return self.parse_lines(logstr.splitlines(), debug)

    def parse_lines(self, lines, debug=False):
        if self.lines != None:
            raise RuntimeError('parse should be called only once')
        self.lines = lines
        document_class_re = re.compile(r'^Document Class: (\w+) ')
        lineno = 1
        numlines = len(self.lines)
        line = ''
        i = 0
        while i < numlines:
            partial = self.lines[i]
            line += partial
            i += 1
            if len(partial) == self.wrap_len:
                if debug:
                    print('partial line: {}'.format(partial))
                continue
            partial = ''
            if debug:
                print(lineno, line)
            error = None
            if debug:
                print(lineno, line)
            # first determine what page we are on.
            ms = pageno_re.findall(line)
            if ms:
                self.current_page = int(ms[-1])
            # This depends upon having used a filepatt in the log to
            # say when files are opened and closed. It fails silently
            # otherwise and we don't know the filepath.
            m = opened_file_re.search(line)
            if m:
                if debug:
                    print('----------------------------------------')
                    print('STACK: {}'.format(str(self.opened_files)))
                    print('file operation on {}'.format(str(m.groups())))
                if m.group('action') == 'opened':
                    filename = m.group('filename')
                    if filename.startswith('./'):
                        filename = filename[2:]
                    self.opened_files.append(filename)
                else:
                    try:
                        self.opened_files.pop()
                    except Exception as e:
                        # I think this should not happen.
                        self.opened_files.append(self.main_file)
                        logging.warning('Warning: the file stack was emptied in log_parser')
            else:
                m = citation_re.search(line)
                if m:
                    error = self._create_error(ErrorType.REFERENCE_ERROR,
                                               line,
                                               lineno)
                    error.pageno = int(m.group(3))
                    if m.group(4):
                        error.filepath_line = int(m.group(4))
                else:
                    m = warning_re.search(line)
                    if m:
                        if debug:
                            print(m.groups())
                        error = self._create_error(ErrorType.LATEX_WARNING,
                                                   line,
                                                   lineno)
                        if self.current_page:
                            error.pageno = self.current_page
                        if m.group(2):
                            error.package = m.group(2)
                        m = line_re.search(line)
                        if m:
                            error.filepath_line = int(m.group('line'))
                    else:
                        m = l3msg_re.search(line)
                        if m:
                            error = self._create_error(ErrorType.LATEX_ERROR,
                                                       line,
                                                       lineno)
                            error.filepath = m.group(1)
                            error.filepath_line = m.group(2)
                            error.package = m.group(4)
                        else:
                            m = error_re.search(line)
                            if m:
                                error = self._create_error(ErrorType.LATEX_ERROR,
                                                           line,
                                                           lineno)
                            else:
                                m = badbox_re.search(line)
                                if m:
                                    typ = m.group(1) # Over or Under
                                    direction = m.group(2) # h or v
                                    if typ == 'Over':
                                        if direction == 'h':
                                            start = m.group(5)
                                            if not start:
                                                start = m.group(7)
                                            error = self._create_error(ErrorType.OVERFULL_HBOX,
                                                                       line,
                                                                       lineno)
                                            error.filepath_line = int(start)
                                        elif direction == 'v':
                                            error = self._create_error(ErrorType.OVERFULL_VBOX,
                                                                       line,
                                                                       lineno)
                                        error.severity = float(m.group(4))
                                    else: # underfull
                                        if direction == 'h':
                                            error = self._create_error(ErrorType.UNDERFULL_HBOX,
                                                                       line,
                                                                       lineno)
                                        else:
                                            error = self._create_error(ErrorType.UNDERFULL_VBOX,
                                                                       line,
                                                                       lineno)
                                        error.severity = float(m.group(3))
                                else:
                                    m = missing_char_re.search(line)
                                    if m:
                                        error = self._create_error(ErrorType.LATEX_WARNING,
                                                                   line,
                                                                   lineno)
                                    else:
                                        m = end_occurred_inside_re.match(line)
                                        if m:
                                            error = self._create_error(ErrorType.LATEX_WARNING,
                                                                       line,
                                                                       lineno)
                                            error.help = 'It appears that you have unbalanced groups in your LaTeX code.'

            line = ''
            lineno = i + 1
            if error and not self.error_ignored(error):
                self.errors.append(error)
                if debug:
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    print(error.json(indent=2))

if __name__ == '__main__':
    """This is just test code."""
    import argparse
    import fnmatch
    import os
    argparser = argparse.ArgumentParser(description='Log parser')
    argparser.add_argument('--class_file',
                           default='iacrcc.cls')
    argparser.add_argument('--main_file',
                           default = 'iacrdoc.tex')
    argparser.add_argument('--log_file',
                           default = 'testdata/logs/iacrdoc.log')
    argparser.add_argument('--verbose',
                           action='store_true')
    args = argparser.parse_args()
    parser = LatexLogParser(main_file=args.main_file, class_file=args.class_file)
    parser.parse_file(Path(args.log_file), debug=args.verbose)
    for error in parser.errors:
        print(error.json(indent=2))
    for root, dirnames, filenames in os.walk('/home/kevin/Downloads/iacrcc/crypto2023'):
        for fname in fnmatch.filter(filenames, '*.log'):
            filename = os.path.join(root, fname)
            logfile = Path(filename)
            jobname = logfile.name.replace('.log', '.tex')
            parser = LatexLogParser(main_file=jobname, class_file=args.class_file)
            print('---------------------{}'.format(filename))
            parser.parse_file(Path(filename), debug=args.verbose)
            for error in parser.errors:
                print(error.json(indent=2))
