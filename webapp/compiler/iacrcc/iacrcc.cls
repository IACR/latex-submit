\def\fileversion{0.1}
\def\filedate{2022/09/04}

\NeedsTeXFormat{LaTeX2e}[1995/12/01]
\typeout{^^J  ***  LaTeX class for IACR Communications in Cryptology v\fileversion\space ***^^J}
\ProvidesClass{iacrcc}[\filedate]

% IACR Communications in Cryptology DOCUMENT CLASS
% Authoritative source is github.com/IACR/latex/iacrcc
% This is originally based on
%   iacrtrans: github.com/Cryptosaurus/iacrtrans
%   acmart: github.com/borisveytsman/acmart
%
% To the extent possible under law, the author(s) have dedicated all
% copyright and related and neighboring rights to this software to the
% public domain worldwide. This software is distributed without any
% warranty.
%
% You should have received a copy of the CC0 Public Domain Dedication
% along with this software. If not, see
% <http://creativecommons.org/publicdomain/zero/1.0/>.
%
%
%%% Class options:
%
%% Document mode
% [version=xxx] where xxx is preprint, submission, or final. The default is preprint.
%               version=submission puts line numbers into the document and makes it
%               anonymous (which can be overridden).
%               version=final is for submitting the final version. This requires a license
%               to be specified and must be compiled with lualatex.
% [notanonymous]  Keep author names in submission mode
%% Package options
% [floatrow]      Load floatrow package with correct captions
% [xcolor=xxx]    Pass xxx to xcolor package
% [hyperref=xxx]  Pass xxx to hyperref package
% [biblatex]      Use the biblatex package instead of bibtex. Note that options
%                 may not be passed to biblatex at this time.
%
%%% HOWTO use this class. See the companion iacrdoc.tex for a better guide.
%
%% Title
% Provide the title of the paper, this should look like:
%\title[running  = {The iacrcc class},
%       onclick  = {https://github.com/IACR/latex},
%       subtitle = {A Template}
%      ]{How to Use the IACR Communications in Cryptology Class}
% Where the options in square brackets “[ ]” are optional and control the following:
% running: The running title displayed in the headers.
% onclick: Define what to do when clicking on the title.
%          This could be used to point to a webpage associated with the paper. 
% subtitle: Provide a subtitle.
%
%% Authors are listed individually using the \addauthor tag followed by a list of affiliations.
% The idea is that every author makes a separate call to this command.
% This should look like:
% \addauthor[inst      = {1,2},
%            orcid     = 0000-0000-0000-0000,
%            footnote  = {Thanks to my supervisor for the support.},
%            onclick   = {https://www.mypersonalwebpage.com}
%           ]{Alice Accomplished}
% Where the options in square brackets “[ ]” are optional 
% and control the following:
% inst:     A numerical list pointing to the index of the institution 
%           in the affiliation array.
% orcid:    Create a small clickable orcid logo next to the authors name 
%           linking to the authors ORCID iD see: orcid.org.
% footnote: Create an author-specific footnote.
% onclick:  Define what to do when clicking on the author name: 
%           e.g., can point to the personal / academic webpage.
% email:    Define the e-mail address of this author.
%
% Affiliations are listed individually using the \affiliations command 
% *after* the (list of) authors using \addauthor.
% This should look like:
% \affiliation[ror        = 05f950310,
%              onclick    = {http://www.kuleuven.be/english},
%              department = {Computer Security and Industrial Cryptography},              
%              street     = {Kasteelpark Arenberg 10, box 2452},
%              city       = {Leuven},
%              state      = {Vlaams-Brabant},
%              postcode   = {3001},
%              country    = {Belgium}
%             ]{KU Leuven}
% Where the options in square brackets “[ ]” are optional and control 
% the following (optional information is mainly used for meta-data collection):
% ror:        Provide the Research Organization Registry (ROR) identifier 
%             for this affiliation (see: ror.org). This is used for meta-data 
%             collection only.
% onclick:    Define what to do when clicking on the affiliation name: 
%             e.g., can point to the affiliation webpage.
% department: Department or suborganization name.
% street:     Street address.
% city:       City name.
% state:      State or province name.
% postcode:   Zip or postal code.
% country:    Country name.
%
% A footnote can be placed on the front page without a symbol / numbering using:
% \genericfootnote{This is the full version of our paper published at XX}

% Common definitions
\RequirePackage{expl3} % used for text_purify on metadata.
% xkeyval is an extension of the keyval package and offers additional macros
% for setting keys and declaring and setting class or package options.
\RequirePackage{xkeyval}
\def\publname{IACR Communications in Cryptology}
\def\IACR@vol{0}
\def\IACR@no{0}
\def\IACR@fp{1}
\def\IACR@lp{\pageref*{LastPage}}
\def\IACR@ISSN{XXXX-XXXX}
\def\IACR@DOI{XXXXXXXX}
\def\IACR@Received{20XX-XX-XX}
\def\IACR@Revised{20XX-XX-XX}
\def\IACR@Accepted{20XX-XX-XX}
\def\IACR@Published{20XX-XX-XX}
\newif\if@IACR@Received \@IACR@Receivedfalse
\newif\if@IACR@Revised \@IACR@Revisedfalse
\newif\if@IACR@Accepted \@IACR@Acceptedfalse
\newif\if@IACR@Published \@IACR@Publishedfalse
% etoolbox is a toolbox of programming facilities geared primarily
% towards LaTeX class and package authors.
\RequirePackage{etoolbox}

\newcommand{\setfirstpage}[1]{\def\IACR@fp{#1}\setcounter{page}{#1}}
\newcommand{\setlastpage}[1]{\def\IACR@lp{#1}}
\newcommand{\setvolume}[1]{\def\IACR@vol{#1}}
\newcommand{\setnumber}[1]{\def\IACR@no{#1}}
\newcommand{\setISSN}[1]{\def\IACR@ISSN{#1}}

% Options
\newif\if@hyperxmp@doi
\@hyperxmp@doifalse
% The jobname.iacrmetadata file will contain accepted \IACR@Received,  \IACR@Accepted,
% \IACR@Published, and \IACR@DOI.
\InputIfFileExists{\jobname.iacrmetadata}{
  \@IACR@Receivedtrue\@IACR@Acceptedtrue\@IACR@Publishedtrue\@hyperxmp@doitrue\typeout{Inserted DOI into PDF}}{}
\newif\if@optbiblatex
\@optbiblatexfalse
\define@key{IACR}{biblatex}[]{\@optbiblatextrue}
\newif\if@floatrow
\@floatrowfalse
\define@key{IACR}{floatrow}[]{\@floatrowtrue}
% version=submission will set anonymous to true, but it can be
% overridden with the notanonymous option for the class.
\newif\if@anonymous
\@anonymousfalse
% This maybe be used to override \@anonymous
\newif\if@notanonymous
\@notanonymousfalse
\define@key{IACR}{notanonymous}[]{\@notanonymoustrue}
\newcommand{\@IACRversion}{preprint}
\define@choicekey{IACR}{version}[\@IACRversion]{preprint,submission,final}[preprint]{}
\define@key{IACR}{xcolor}{\PassOptionsToPackage{#1}{xcolor}}
\define@key{IACR}{hyperref}{\PassOptionsToPackage{#1}{hyperref}}
% TODO: figure out how to prohibit passing twocolumn and landscape to article.
%\DeclareOptionX*{
%  \typeout{passing \CurrentOption to article}\PassOptionsToClass{\CurrentOption}{article}
%}
\DeclareOptionX*{}
\ProcessOptionsX<IACR>\relax
\typeout{Compiling version=\@IACRversion}
\ifcsstring{@IACRversion}{submission}{
  \if@notanonymous\@anonymousfalse
  \typeout{Disabling anonymity}
  \else
  \@anonymoustrue
  \typeout{Setting to anonymous}
  \fi
}{}
\ifcsstring{@IACRversion}{final}{
  % This disabled boxes for overfull hboxes.
  \PassOptionsToClass{final}{article}
}{}

% article class
\LoadClass[10pt,twoside]{article}[2007/10/19]

% iftex: Am I running under pdfTEX, XETEX or LuaTEX?
\RequirePackage{iftex}

\ifluatex
  % Fixes for mathematics-related LuaLATEX issues
  \RequirePackage{lualatex-math}
\fi

% xcolor starts from the basic facilities of the color package, 
% and provides easy driver-independent access to several kinds 
% of color tints, shades, tones, and mixes of arbitrary colors. I
\RequirePackage{xcolor}

% xstring provides macros for manipulating strings - testing a string’s 
% contents, extracting substrings, substitution of substrings and providing
% numbers such as string length, position of, or number of recurrences of, 
% a substring.
% Required for IfSubStr
\RequirePackage{xstring}

% The hyperref package is used to handle cross-referencing commands in 
% LaTeX to produce hypertext links in the document. 
% Hyperref must be loaded last, but before other AtEndPreamble hooks  
\AtEndPreamble{
  \@ifpackageloaded{hyperref}{}{\RequirePackage{hyperref}}
  \hypersetup{pdflang=en}
  \hypersetup{urlcolor=cyan}
  \hypersetup{colorlinks=true,
    citecolor=black!70!green,
    linkcolor=black!70!red}
  % Disable latexdiff commands in PDF links
  \pdfstringdefDisableCommands{%
    \def\DIFadd#1{#1}%
    \def\DIFdel#1{}%
  }
  % Old versions of hyperxmp do not support DOI
  \@ifpackagelater{hyperxmp}{2019/03/14}{\@hyperxmp@doitrue\hypersetup{keeppdfinfo=true}}{}
}

% Check the character encoding. lualatex and unicode are required for final versions.
% We allow pdflatex to be used for preprint and submission modes, because it is faster
% than lualatex.
\ifcsstring{encodingdefault}{TU}{}{ % not unicode
  \ifcsstring{@IACRversion}{final}{
    \ifluatex
      \ClassError{iacrcc}{^^JThe font encoding \encodingdefault is not supported.
      Do not use the fontenc package, and use only unicode fonts.}{}
    \else
      \ClassError{iacrcc}{^^Jfinal versions must be compiled with lualatex.^^J}{}
    \fi
  }{%
    \ifluatex
      \ClassError{iacrcc}{^^JThe font encoding \encodingdefault is not supported.\MessageBreak
        Do not use the fontenc package, and use only unicode fonts.}{}
       \usepackage[TU]{fontenc}
     \else
      \ClassWarning{iacrcc}{^^J This package is intended to be used with lualatex\MessageBreak
        because pdflatex does not support unicode output.^^J}{}
    \fi
    % set the default encoding to TU.
  }
}

% XMP (eXtensible Metadata Platform) is a mechanism proposed by Adobe 
% for embedding document metadata within the document itself.
\RequirePackage{hyperxmp} % hyperxmp 5.x has issues with AtEndPreamble
\setcounter{tocdepth}{2}

% Geometry
\RequirePackage[a4paper,hscale=0.65,vscale=0.75,marginratio=1:1,marginparwidth=2.7cm]{geometry}

% afterpage implements a command that causes the commands specified 
% in its argument to be expanded after the current page is output
\RequirePackage{afterpage}

% Title fonts: bf+sf
% The secsty package to help change the style of any or all of LaTeX's 
% sectional headers in the article, book, or report classes.
\RequirePackage{sectsty}
\allsectionsfont{\sffamily\boldmath}
% Also for descriptions
\renewcommand*\descriptionlabel[1]{\hspace\labelsep
                                   \normalfont\bfseries\sffamily\boldmath #1}

% Make some counters robust that are made fragile by `calc` needed for orcidlink
\robustify\setcounter
\robustify\addtocounter
\robustify\setlength
\robustify\addtolength

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% This provides a command to insert the ORCiD logo, which is hyperlinked to 
% the URL of the researcher whose iD was specified.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% This copies over definition of the orcidlink from the orcidlink style file
% by by Leo C. Stein which in turn is a package around Milo's code on TeX.SE,
% see https://tex.stackexchange.com/a/445583/34063

\RequirePackage{tikz}
\ProcessOptions\relax
\usetikzlibrary{svg.path}

\definecolor{orcidlogocol}{HTML}{A6CE39}
\tikzset{
  orcidlogo/.pic={
    \fill[orcidlogocol] svg{M256,128c0,70.7-57.3,128-128,128C57.3,256,0,198.7,0,128C0,57.3,57.3,0,128,0C198.7,0,256,57.3,256,128z};
    \fill[white] svg{M86.3,186.2H70.9V79.1h15.4v48.4V186.2z}
                 svg{M108.9,79.1h41.6c39.6,0,57,28.3,57,53.6c0,27.5-21.5,53.6-56.8,53.6h-41.8V79.1z M124.3,172.4h24.5c34.9,0,42.9-26.5,42.9-39.7c0-21.5-13.7-39.7-43.7-39.7h-23.7V172.4z}
                 svg{M88.7,56.8c0,5.5-4.5,10.1-10.1,10.1c-5.6,0-10.1-4.6-10.1-10.1c0-5.6,4.5-10.1,10.1-10.1C84.2,46.7,88.7,51.3,88.7,56.8z};
  }
}

% Reciprocal of the height of the svg whose source is above.  The
% original generates a 256pt high graphic; this macro holds 1/256.
\newcommand{\@OrigHeightRecip}{0.00390625}

% We will compute the current X height to make the logo the right height
\newlength{\@curXheight}

\DeclareRobustCommand\orcidlink[1]{%
\texorpdfstring{%
\setlength{\@curXheight}{\fontcharht\font`X}%
\href{https://orcid.org/#1}{\XeTeXLinkBox{\mbox{%
\begin{tikzpicture}[yscale=-\@OrigHeightRecip*\@curXheight,
xscale=\@OrigHeightRecip*\@curXheight,transform shape]
\pic{orcidlogo};
\end{tikzpicture}%
}}}}{}}

% End of macros for orcidlink
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% pgfkeys is a flexible key management system
% The package provides a flexible key management system, whose keys are 
% arranged in a tree-like structure; key values may be functions as well 
% as strings or numbers.
\RequirePackage{pgfkeys}

\pgfkeys{/IACR-author/entities/.cd,
  inst/.initial=\@empty,
  orcid/.initial=\@empty,
  footnote/.initial=\@empty,
  onclick/.initial=\@empty,
  email/.initial=\@empty,
  }
\def\IACR@author@params@set@keys#1{%%
  \pgfkeys{/IACR-author/entities/.cd,#1}}
\def\IACR@author@params@get#1{%%
  \pgfkeysvalueof{/IACR-author/entities/#1}}
\newcommand\IACR@author@params@clearkeys{%
  \IACR@author@params@set@keys{inst=\@empty,orcid=\@empty,footnote=\@empty,onclick=\@empty,email=\@empty}%
}

\pgfkeys{/IACR-affiliation/entities/.cd,
  ror/.initial=\@empty,
  onclick/.initial=\@empty,
  department/.initial=\@empty,
  street/.initial=\@empty,
  city/.initial=\@empty,
  state/.initial=\@empty,
  postcode/.initial=\@empty,
  country/.initial=\@empty,
  }
\def\IACR@affiliation@params@set@keys#1{%%
  \pgfkeys{/IACR-affiliation/entities/.cd,#1}}
\def\IACR@affiliation@params@get#1{%%
  \pgfkeysvalueof{/IACR-affiliation/entities/#1}}
\newcommand\IACR@affiliation@params@clearkeys{%
  \IACR@affiliation@params@set@keys{ror=\@empty,onclick=\@empty,department=\@empty,street=\@empty,city=\@empty,state=\@empty,postcode=\@empty,country=\@empty}%
}

\pgfkeys{/IACR-title/entities/.cd,
  running/.initial=\@empty,
  onclick/.initial=\@empty,
  subtitle/.initial=\@empty,
  }
\def\IACR@title@params@set@keys#1{%%
  \pgfkeys{/IACR-title/entities/.cd,#1}}
\def\IACR@title@params@get#1{%%
  \pgfkeysvalueof{/IACR-title/entities/#1}}
\newcommand\IACR@title@params@clearkeys{%
  \IACR@title@params@set@keys{running=\@empty,onclick=\@empty,subtitle=\@empty}%
}

\pgfkeys{/IACR-license-CC-by/entities/.cd,
  file/.initial={CC-by.png},
  text/.initial={Creative Commons License CC-BY 4.0.},
  url/.initial={http://creativecommons.org/licenses/by/4.0/},
  }
\def\IACR@license-CC-by@params@get#1{%%
  \pgfkeysvalueof{/IACR-license-CC-by/entities/#1}}

% Title/Author/affiliations
\global\let\IACR@runningauthors\@empty
\global\let\@author\@empty
\global\let\@affiliation\@empty

\newcounter{IACR@author@cnt}
\newcounter{IACR@inst@cnt}
\newif\if@IACR@autoinst
\@IACR@autoinsttrue
\def\IACR@author@last{0}

% Meta information is written out in [jobname].meta
\newwrite\meta
\immediate\openout\meta=\jobname.meta
\newcount\num@authors
\num@authors=0\relax
\newcount\num@affil
\num@affil=0\relax

\AtEndDocument{
  \immediate\closeout\meta%
  % Check if either \title, \addauthor or \affiliation macros were redefined
  % Also check if the font (\familydefault) or the margings (\paperwidth) were modified.
  % Throw an error if so, these are needed for meta-data collection
  \ifx\store@addauthor\addauthor\else
    \ClassError{iacrcc}{The \string\addauthor\space macro seems to be redefined}{}%
  \fi
  \ifx\store@title\title\else
    \ClassError{iacrcc}{The \string\title\space macro seems to be redefined}{}%
  \fi
  \ifx\store@affiliation\affiliation\else
    \ClassError{iacrcc}{The \string\affiliation\space macro seems to be redefined}{}%
  \fi
  \ifx\store@font\familydefault\else
    \ClassError{iacrcc}{The \string\familydefault\space macro seems to be redefined}{}%
  \fi
  \ifx\store@paperwidth\paperwidth\else
    \ClassError{iacrcc}{The \string\paperwidth\space macro seems to be redefined}{}%
  \fi
  % final version requires abstract.
  \ifcsstring{@IACRversion}{final}{
    \IfFileExists{\jobname.abstract}{}{\ClassError{iacrcc}{An abstract with abstract environment is required}{}}
  }{}
}

% latex3 syntax used for writing text to the .meta file. This requires
% a TeX distribution from 2020 or later.
\ExplSyntaxOn
\ifdefined\text_purify:n
\else
\ClassWarningNoLine{iacrcc}{The .meta file may be ill-formed.}
\fi
\cs_new:Npn\@writemeta#1{
  \ifdefined\text_purify:n
  \immediate\write\meta{\text_purify:n #1}
  \else
  \immediate\write\meta{#1}
  \fi
}
\ExplSyntaxOff

\renewcommand\maketitle{\par
  \@writemeta{version: \@IACRversion}
  \@writemeta{title: \@plaintitle}%
  \ifx\@subtitle\@empty\else
    \@writemeta{\IACRSS subtitle: \@subtitle}
  \fi
  \ifx\@genericfootnote\@empty\else
    \renewcommand\thefootnote{}\footnotetext{\@genericfootnote}%
  \fi
  \ifx\@displayemails\@empty\else
    \renewcommand\thefootnote{}\footnotetext{\@displayemails}%
  \fi
  \begingroup
    \renewcommand\thefootnote{\@fnsymbol\c@footnote}%
    \long\def\@makefntext##1{\parindent 1em\noindent
            \hb@xt@1.8em{%
                \hss\@textsuperscript{\normalfont\@thefnmark}}##1}%
    \newpage
    \global\@topnum\z@   % Prevents figures from going at top of page.
    \@maketitle
    \thispagestyle{title}\@thanks
  \endgroup
  \setcounter{footnote}{0}%
  \global\let\thanks\relax
  \global\let\maketitle\relax
  \global\let\@maketitle\relax
  \global\let\@thanks\@empty
  \global\let\@date\@empty
  \global\let\date\relax
  \global\let\and\relax
  % Adjust header size for title page
  \addtolength{\headheight}{\baselineskip}%
  \addtolength{\headsep}{-\baselineskip}%
  \afterpage{%
    \global\advance\headheight by -\baselineskip%
    \global\advance\headsep by \baselineskip%
  }%
}

% Add support to display provided e-mail addresses 
% in the footnote of the front page
\global\let\@displayemails\@empty

% Add support for a footnote without symbol on the front page
\global\let\@genericfootnote\@empty
\newcommand\genericfootnote[1]{
  \gdef\@genericfootnote{#1}%
}

\def\@maketitle{%
  % Count authors and affiliations
  \setcounter{IACR@author@cnt}{1}%
  \setcounter{IACR@inst@cnt}{1}%
  \setbox0\hbox{\def\thanks##1{\global\@IACR@autoinstfalse}\def\inst##1{\global\@IACR@autoinstfalse}\def\and{\stepcounter{IACR@author@cnt}}\@author}%
  \setbox0\hbox{\def\and{\stepcounter{IACR@inst@cnt}}\@affiliation}%
  \xdef\IACR@author@last{\theIACR@author@cnt}%
  \edef\IACR@inst@last{\theIACR@inst@cnt}%
  \ifnum\IACR@author@last=\IACR@inst@last\else\@IACR@autoinstfalse\fi
  \ifnum\IACR@author@last=1 \@IACR@autoinstfalse\fi
  \newpage
  \null
  \vskip 2em%
  \begin{center}%
  \let \footnote \thanks
    {\def\@makefnmark{\rlap{\@textsuperscript{\normalfont\@thefnmark}}}%
      {\LARGE \bfseries\sffamily\boldmath \@title\par}
    \ifdefined\@subtitle\vskip .5em{\large\sffamily\bfseries\@subtitle\par}\fi}%
    \vskip 1.5em%
    {\large
      \lineskip .5em%
        \if@anonymous
          Anonymous Submission
        \else
          \setcounter{IACR@author@cnt}{1}%
          \def\and{\if@IACR@autoinst\inst{\theIACR@author@cnt} \fi
            \stepcounter{IACR@author@cnt}%
            \ifnum\theIACR@author@cnt=\IACR@author@last\unskip\space and \ignorespaces\else\unskip, \ignorespaces\fi}
          \@author\if@IACR@autoinst\inst{\theIACR@author@cnt}\fi
          \vskip 1em\par
          \small
          \setcounter{IACR@author@cnt}{1}%        
          % When there is only one author with one or more affiliations
          % do not display the affiliation counter
          \def\and{\par\ifnum\num@authors=1\relax\else\stepcounter{IACR@author@cnt}$^\theIACR@author@cnt$~\fi}
          \ifnum\num@authors=1\relax\else
            \ifnum\IACR@inst@last>1 $^1$~\fi\ignorespaces%
          \fi
          \@affiliation
        \fi%!anonymous
      }%
  \end{center}%
  \par
  \vskip 1.5em}

% This is for indentation in meta file.
\newcommand{\IACRSS}{\space\space}

% We do not support \author, use \addauthor instead
\renewcommand\author[2][]{\ClassError{iacrcc}{%
  Do not use the \string\author\space macro: use the \string\addauthor\space macro instead}{}%
}

\newcommand\surname[1]{#1}

\newcommand\addauthor[2][]{%    
  % Some very basic checking if addauthor is used correctly
  % Check if the name contains an "," this might be correct (e.g., Alice, Jr)
  \IfSubStr{\detokenize{#2}}{,}{\ClassWarning{iacrcc}{%
      Do not put several authors in the same \string\addauthor\space macro!}}{}%
  % Affiliations should be defined *after* addauthor
  \ifnum\num@affil>0\relax
    \ClassError{iacrcc}{affiliations must follow authors}{}%
  \fi
  % Do not use " and " in your author name: this might indicate incorrect usage
  % The usage of "\and" will not and throw an error.
  \IfSubStr{#2}{ and }{\ClassError{iacrcc}{%
      Do not put several authors in the same \string\addauthor\space macro!}{}}{}%   
  \global\advance\num@authors by 1\relax%
  %
  % Write out the author in the meta file.
  \@writemeta{author:}%
  \@writemeta{\IACRSS name: #2}%
  \renewcommand\surname[1]{##1}%
  \IACR@author@params@set@keys{#1}%
  \@writemeta{\IACRSS affil: \IACR@author@params@get{inst}}%
  \edef\@IACRorcid{\IACR@author@params@get{orcid}}%
  \edef\@IACRfootnote{\IACR@author@params@get{footnote}}%
  \edef\@IACRonclick{\IACR@author@params@get{onclick}}%
  \edef\@IACRinst{\IACR@author@params@get{inst}}%
  \edef\@IACRemail{\IACR@author@params@get{email}}%
  % Create the unlabeled footnote consisting of:
  % First the provided footnote (if any) and next
  % the provided e-mail addresses
  \ifx\@IACRemail\@empty\else
    \ifx\@displayemails\@empty
      \edef\@displayemails{E-mail: \noexpand\url{\@IACRemail}~(#2)}%
    \else
      \eappto\@displayemails{, \noexpand\url{\@IACRemail}~(#2)}%
    \fi
    \@writemeta{\IACRSS email: \@IACRemail}%
  \fi
  % Author name + optionally clickable
  \ifx\@author\@empty
    \ifx\@IACRonclick\@empty
      \def\@author{#2}%
    \else
      \edef\@author{\noexpand\href{\@IACRonclick}{\noexpand\color{black}{#2}}}%
    \fi
    \def\IACR@runningauthors{#2}%
  \else
    \ifx\@IACRonclick\@empty
      \appto\@author{\and#2}%
    \else
      \eappto\@author{\noexpand\and\noexpand\href{\@IACRonclick}{\noexpand\color{black}{#2}}}%
    \fi
    \appto\IACR@runningauthors{,\space#2}%
  \fi
  % Add the footnote text if present
  \ifx\@IACRfootnote\@empty\else
    \eappto\@author{\noexpand\footnote{\@IACRfootnote}}%
  \fi
  \ifx\@IACRorcid\@empty\else
    \eappto\@author{~\noexpand\orcidlink{\@IACRorcid}}%
    \@writemeta{\IACRSS orcid: \@IACRorcid}%
  \fi
  \ifx\@IACRinst\@empty\else
    \eappto\@author{\noexpand\inst{\@IACRinst}}%
  \fi
  \IACR@author@params@clearkeys%
}

\let\store@addauthor\addauthor  % Save macro away

% Provide the title of the paper
\renewcommand\title[2][]{%
  \IACR@title@params@set@keys{#1}%
  \edef\@IACRrunning{\IACR@title@params@get{running}}%
  \edef\@IACRonclick{\IACR@title@params@get{onclick}}%
  \edef\@IACRsubtitle{\IACR@title@params@get{subtitle}}%
  \gdef\@plaintitle{#2}
  \ifx\@IACRrunning\@empty
    \gdef\IACR@runningtitle{#2}%
  \else
    \gdef\IACR@runningtitle{\@IACRrunning}%
  \fi  
  \ifx\@IACRonclick\@empty
    \edef\@title{#2}%
  \else
    \edef\@title{\noexpand\href{\@IACRonclick}{\noexpand\color{black}{#2}}}%
  \fi
  \ifx\@IACRsubtitle\@empty
    \gdef\@subtitle{\@empty}%
  \else
    \gdef\@subtitle{\@IACRsubtitle}%
  \fi
  \IACR@title@params@clearkeys%
}

\let\store@title\title  % Save macro away

\newcommand\affiliation[2][]{%
  \global\advance\num@affil by 1\relax% 
  \@writemeta{affiliation:}%
  \@writemeta{\IACRSS name: \unexpanded{#2}}%
  \IACR@affiliation@params@set@keys{#1}%%
  \edef\@IACRror{\IACR@affiliation@params@get{ror}}%
  \edef\@IACRonclick{\IACR@affiliation@params@get{onclick}}%
  \edef\@IACRdepartment{\IACR@affiliation@params@get{department}}%
  \edef\@IACRstreet{\IACR@affiliation@params@get{street}}%
  \edef\@IACRcity{\IACR@affiliation@params@get{city}}%
  \edef\@IACRstate{\IACR@affiliation@params@get{state}}%
  \edef\@IACRpostcode{\IACR@affiliation@params@get{postcode}}%
  \edef\@IACRcountry{\IACR@affiliation@params@get{country}}%
  \ifx\@IACRror\@empty\else
    \@writemeta{\IACRSS ror: \@IACRror}%
  \fi  
  \ifx\@IACRdepartment\@empty\else
    \@writemeta{\IACRSS department: \@IACRdepartment}%
  \fi
  \ifx\@IACRstreet\@empty\else
    \@writemeta{\IACRSS street: \@IACRstreet}%
  \fi
  \ifx\@IACRcity\@empty\else
    \@writemeta{\IACRSS city: \@IACRcity}%
  \fi
  \ifx\@IACRstate\@empty\else
    \@writemeta{\IACRSS state: \@IACRstate}%
  \fi
  \ifx\@IACRpostcode\@empty\else
    \@writemeta{\IACRSS postcode: \@IACRpostcode}%
  \fi
  \ifx\@IACRcountry\@empty\else
    \@writemeta{\IACRSS country: \@IACRcountry}%
  \fi
  \ifx\@IACRonclick\@empty
    \ifx\@affiliation\@empty
      \gdef\@affiliation{\unexpanded{#2}}%
    \else
      \appto\@affiliation{\and\unexpanded{#2}}%
    \fi
  \else
    \ifx\@affiliation\@empty
      \edef\@affiliation{\noexpand\href{\@IACRonclick}{\noexpand\color{black}{\unexpanded{#2}}}}%
    \else
      \eappto\@affiliation{\noexpand\and{\noexpand\href{\@IACRonclick}{\noexpand\color{black}{\unexpanded{#2}}}}}%
    \fi
  \fi
  \IACR@affiliation@params@clearkeys%
}

\let\store@affiliation\affiliation  % Save macro away

\if@anonymous
  \gdef\@author{Anonymous Submission to \publname}%
  \gdef\IACR@runningauthors{}
  \renewcommand{\addauthor}[2][]{}%
  \renewcommand{\affiliation}[2][]{}%
\fi

\newcommand{\inst}[1]{%
  \ifnum\num@authors=1\relax\else
    \ifnum\num@affil=1\relax\else
      \unskip$^{#1}$%
    \fi
  \fi}
  
\def\fnmsep{\unskip$^,$}

% Head/foot
% The fancyhdr package provides extensive facilities, both for constructing 
% headers and footers, and for controlling their use.
\RequirePackage{fancyhdr}

% The graphicx package builds upon the graphics package, providing a key-value
% interface for optional arguments to the \includegraphics command. 
% This interface provides facilities that go far beyond what the graphics 
% package offers on its own.
\RequirePackage{graphicx}

% if the author decides to use biblatex, then we pass options for the style to enforce
% consistent look and feel.
\if@optbiblatex
  \typeout{biblatex options may not be changed with \@backslashchar usepackage}
  \RequirePackage[backend=biber,style=alphabetic,maxbibnames=4]{biblatex}[2019/12/01]
  % We use a sourcemap to copy certain fields to the side so we can
  % include them in the .meta file. biblatex makes it hard to recover
  % some fields intact such as AUTHOR, EDITOR, PUBLISHER, LOCATION, and
  % PAGES. biber is able to parse these, but they get rewritten in a way
  % that is inconvenient to copy them to the .meta file. There may
  % be a better way to do this, but biblatex is complicated.
  \DeclareNameFormat{author}{%
    \usebibmacro{name:given-family}{\namepartfamily}{\namepartgiven}{\namepartprefix}{\namepartsuffix}%
    \usebibmacro{name:andothers}%
    {\renewcommand{\bibnamedelima}{ }\renewcommand{\bibnamedelimi}{ }%
      \@writemeta{\IACRSS author: \expanded{\namepartgiven\ifdefvoid{\namepartprefix}{}{ \namepartprefix } \namepartfamily\ifdefvoid{\namepartsuffix}{}{, \namepartsuffix}}}%
      \@writemeta{\IACRSS surname:\ifdefvoid{\namepartprefix}{}{ \namepartprefix} \namepartfamily}}
  }
  \DeclareSourcemap{
    \maps[datatype=bibtex,overwrite=true]{
      \map{% copy author to usera
        \step[fieldsource=author,]
        \step[fieldset=usera,origfieldval,append]
      }
      \map[overwrite]{% copy editor to userb
        \step[fieldsource=editor,]
        \step[fieldset=userb,origfieldval,append]
      }
      \map[overwrite]{% copy institution to userc
        \step[fieldsource=institution,]
        \step[fieldset=userc,origfieldval,append]
      }
      \map[overwrite]{% copy publisher to userd
        \step[fieldsource=publisher,]
        \step[fieldset=userd,origfieldval,append]
      }
      \map[overwrite]{% copy location to usere
        \step[fieldsource=location,]
        \step[fieldset=usere,origfieldval,append]
      }
      \map[overwrite]{% copy organization to userf
        \step[fieldsource=organization,]
        \step[fieldset=userf,origfieldval,append]
      }
      \map[overwrite]{% copy pages to verba
        \step[fieldsource=pages,]
        \step[fieldset=verba,origfieldval,append]
      }
      \map[overwrite]{% copy date to verbb
        \step[fieldsource=date,]
        \step[fieldset=verbb,origfieldval,append]
      }
    }
  }
  \AtEndPreamble{
    % TODO: this does not handle ~ properly. Maybe other primitives?
    \newcommand{\@writemkv}[2]{%
      \ifstrempty{\@metaval}{}{\@writemeta{\IACRSS #1: #2}}}
    \AtEveryBibitem{
      \@writemeta{citation: \strfield{entrytype} \strfield{entrykey}}
      \iffieldundef{title}{}{\@writemkv{title}{\strfield{title}}}
      \iffieldundef{subtitle}{}{\@writemkv{subtitle}{\strfield{subtitle}}}
      \iffieldundef{booktitle}{}{\@writemkv{booktitle}{\strfield{booktitle}}}
      \iffieldundef{journaltitle}{}{\@writemkv{journal}{\strfield{journaltitle}}}
      \iffieldundef{edition}{}{\@writemkv{edition}{\strfield{edition}}}
      \iffieldundef{volume}{}{\@writemkv{volume}{\strfield{volume}}}
      \iffieldundef{number}{}{\@writemkv{number}{\strfield{number}}}
      \iffieldundef{issue}{}{\@writemkv{issue}{\strfield{issue}}}
      \iffieldundef{series}{}{\@writemkv{series}{\strfield{series}}}
      \iffieldundef{chapter}{}{\@writemkv{chapter}{\strfield{chapter}}}
      \iffieldundef{year}{}{\@writemkv{year}{\strfield{year}}}
      \iffieldundef{month}{}{\@writemkv{month}{\strfield{month}}}
      \iffieldundef{note}{}{\@writemkv{note}{\strfield{note}}}
      \iffieldundef{usera}{}{\@writemkv{authors}{\strfield{usera}}}
      \iffieldundef{userb}{}{\@writemkv{editors}{\strfield{userb}}}
      \iffieldundef{userc}{}{\@writemkv{institution}{\strfield{userc}}}
      \iffieldundef{userd}{}{\@writemkv{publisher}{\strfield{userd}}}
      \iffieldundef{usere}{}{\@writemkv{address}{\strfield{usere}}}
      \iffieldundef{userf}{}{\@writemkv{organization}{\strfield{userf}}}
      \iffieldundef{verba}{}{\@writemkv{pages}{\strfield{verba}}}
      \iffieldundef{verbb}{}{\@writemkv{date}{\strfield{verbb}}}
      \iffieldundef{urlraw}{}{\@writemkv{url}{\strfield{urlraw}}}
      % unused. This escapes things like \
      % \iffieldundef{url}{}{\@writemeta{\IACRSS url: \strfield{url}}}
      \iffieldundef{doi}{}{\@writemkv{doi}{\strfield{doi}}}
      \iffieldundef{isbn}{}{\@writemkv{isbn}{\strfield{isbn}}}
      \iffieldundef{issn}{}{\@writemkv{issn}{\strfield{issn}}}
      \iffieldundef{keywords}{}{\@writemkv{keywords}{\strfield{keywords}}}
      \iffieldundef{howpublished}{}{\@writemkv{howpublished}{\strfield{howpublished}}}
      % TODO: maybe include eprint, eprintclass, eprinttype
    }
  }
\else % did not invoke \documentclass[biblatex]{iacrcc}
  \AtBeginDocument{
    \@ifpackageloaded{biblatex}{\ClassError{iacrcc}{biblatex should be loaded with \@backslashchar documentclass[biblatex]{iacrcc}}}
  }
\fi%!biblatex

\ifcsstring{@IACRversion}{final}{
  % recent versions of hyperxmp load totpages, which conflicts with lastpage
    \@ifpackageloaded{totpages}{
      \def\IACR@lp{\pageref*{TotPages}}
    }{
      \RequirePackage{lastpage}
    }
}{}


\global\let\@IACR@License\@empty%
\newcommand\license[1]{
  \gdef\@IACR@License{#1}%
}

\fancypagestyle{title}{%
  \fancyhf{} % clear all header and footer fields
  \ifcsstring{@IACRversion}{final}{
      \ifx\@IACR@License\@empty
        \ClassError{iacrcc}{Please specify a license when using version=final.}{}%
      \else
        \def\@IACR@CCby{CC-by}%
        \ifx\@IACR@License\@IACR@CCby%
          \edef\@IACRLicenseFile{\IACR@license-CC-by@params@get{file}}%
          \edef\@IACRLicenseText{\IACR@license-CC-by@params@get{text}}%
          \edef\@IACRLicenseUrl{\IACR@license-CC-by@params@get{url}}%
        \else
          \ClassError{iacrcc}{Invalid license: \@IACR@License. Please provide one of { CC-by }.}{}%
        \fi
      \fi
      \fancyhead[L]{%
        \small%
        \publname{}\\
        ISSN~\IACR@ISSN, Vol.~\IACR@vol, No.~\IACR@no, pp.~\IACR@fp--\IACR@lp. \hfill{}%
        \href{https://doi.org/\IACR@DOI}{DOI:\IACR@DOI}%
      }
      \fancyfoot[L]{%
        \small%
        Licensed under %
        \href{\@IACRLicenseUrl}{\@IACRLicenseText}%
        \hfill{}%
        \includegraphics[clip,height=2ex]{\@IACRLicenseFile}\\[.1em]%
        \if@IACR@Received Received: \IACR@Received \hfill{} \fi%
        \if@IACR@Revised Revised: \IACR@Revised \hfill{} \fi%
        \if@IACR@Accepted Accepted: \IACR@Accepted \hfill{} \fi%
        \if@IACR@Published Published: \IACR@Published \fi%
      }%
      \hypersetup{pdfcopyright={Licensed under \@IACRLicenseText}}
      \hypersetup{pdflicenseurl={\@IACRLicenseUrl}}
      \hypersetup{pdfsubject={\publname{}, DOI:\IACR@DOI}}
  }{} % final
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0pt}
}%fancypagestyle

\fancyhf{}
\fancyhead[RO,LE]{\thepage}
\fancyhead[RE]{\IACR@runningtitle}%
\fancyhead[LO]{%
  \if@anonymous
    \def\thanks##1{}%
    \def\inst##1{}%
    \def\fnmsep{}%
    \def\\{}%
    \def\footnote##1{}%
    \setcounter{IACR@author@cnt}{1}%
    \@author%
  \else
    \IACR@runningauthors%
  \fi%!anonymous
}

\renewcommand{\markboth}[2]{}
\pagestyle{fancy}

%Abstract style, keywords
\global\let\@IACR@print@keywords\@empty
\def\@IACR@keywords{No keywords given.}

\def\keywords{\@ifnextchar[{\IACR@@@keywords}{\IACR@@keywords}}
\def\IACR@@@keywords[#1]#2{
  \gdef\@IACR@PDFkeywords{#1}%
  \gdef\@IACR@keywords{#2}%
  \gdef\@IACR@print@keywords{\unexpanded{#2}}%
}
\def\IACR@@keywords#1{%
  \gdef\@IACR@keywords{#1}%
  \gdef\@IACR@print@keywords{\unexpanded{#1}}%
}

% Sophisticated verbatim text
\RequirePackage{fancyvrb} % used to write the abstract into \jobname.abstract

\renewenvironment{abstract}{%
  \def\and{,\space}\edef\@writekeywords{\@IACR@keywords}%
  \@writemeta{keywords: \@IACR@print@keywords}%
  \small\quotation\setlength{\parindent}{0pt}\noindent
  \textbf{\textsf{Abstract.}}
  \VerbatimOut{\jobname.abstract}}{
  \endVerbatimOut
  \input{\jobname.abstract}
  \smallskip\par\textbf{\textsf{Keywords:}}
    \def\and{\unskip\space\textperiodcentered\space\ignorespaces}\@IACR@keywords
  \endquotation%
  %% PDF keywords
  \def\and{, }%
  \def\thanks##1{}%
  \def\footnote##1{}%
  \def\inst##1{}%
  \def\fnmsep{}%
  \def\\{}%
  \def\zap@first@space ##1{##1}
  \def\insert@last@space##1,##2{%
    ##1%
    \ifx##2\@empty\space\else, \expandafter\insert@last@space##2\fi}
  \def\zap@comma@space##1 ,##2{%
    ##1%
    \ifx##2\@empty\else, \expandafter\zap@comma@space##2\fi}
  \def\zap@dbl@space##1 ##2{%
    ##1%
    \ifx##2\@empty\else\space\expandafter\zap@dbl@space##2\fi}
  \ifdefined\@IACR@PDFkeywords
    \hypersetup{pdfkeywords=\@IACR@PDFkeywords}
  \else
    \protected@edef\@tmp{\expandafter\@IACR@keywords}
    \protected@edef\@tmp{\expandafter\insert@last@space\@tmp,\@empty}
    \protected@edef\@tmp{\expandafter\zap@comma@space\@tmp ,\@empty}
    \protected@edef\@tmp{\expandafter\insert@last@space\@tmp,\@empty}
    \protected@edef\@tmp{\expandafter\zap@dbl@space\@tmp \@empty}
    \protected@edef\@tmp{\expandafter\zap@first@space \@tmp}
    \hypersetup{pdfkeywords=\@tmp}
  \fi
  %% PDF author
  \def\zap@one##1,##2{##1}
  \def\zap@last##1,##2{\ifx##1\@empty\else\space and \expandafter\zap@one##1\fi}
  \def\zap@last@comma##1,##2,##3{%
    ##1%
    \ifx##3\@empty%
    \expandafter\zap@last\else
    ,\expandafter\zap@last@comma\fi%
    ##2,##3}
  \if@anonymous
    \hypersetup{pdfauthor={hidden for submission}}
  \else
    \hypersetup{pdfauthor=\IACR@runningauthors}
  \fi%!anonymous
  %% PDF title
  \hypersetup{pdftitle=\@plaintitle}
  % PDF metadata
  \ifcsstring{@IACRversion}{final}{
    \if@hyperxmp@doi{
      \hypersetup{%
        pdfdoi=\IACR@DOI,%
        pdfissn=\IACR@ISSN,%
        pdfpubtype=journal,%
        pdfpublication=\publname,%
        pdfvolumenum=\IACR@vol,%
        pdfissuenum=\IACR@no,%
        pdfpagerange={\IACR@fp-\IACR@lp},%
    }}
    \fi%hyperxmp@doi
  }{} % final
}

% autoref: capitals for Sections, and adding Algorithm
\def\equationautorefname{Equation}%
\def\footnoteautorefname{footnote}%
\def\itemautorefname{item}%
\def\figureautorefname{Figure}%
\def\tableautorefname{Table}%
\def\partautorefname{Part}%
\def\appendixautorefname{Appendix}%
\def\chapterautorefname{Chapter}%
\def\sectionautorefname{Section}%
\def\subsectionautorefname{Subsection}%
\def\subsubsectionautorefname{Subsubsection}%
\def\paragraphautorefname{paragraph}%
\def\subparagraphautorefname{subparagraph}%
\def\FancyVerbLineautorefname{line}%
\def\theoremautorefname{Theorem}%
\def\pageautorefname{page}%

\def\algorithmautorefname{Algorithm}

\def\definitionautorefname{Definition}
\def\exampleautorefname{Example}
\def\exerciseautorefname{Exercise}
\def\propertyautorefname{Property}
\def\questionautorefname{Question}
\def\solutionautorefname{Solution}
\def\propositionautorefname{Proposition}
\def\problemautorefname{Problem}
\def\lemmaautorefname{Lemma}
\def\conjectureautorefname{Conjecture}
\def\corollaryautorefname{Corollary}
\def\claimautorefname{Claim}
\def\remarkautorefname{Remark}
\def\noteautorefname{Note}
\def\caseautorefname{Case}

% amsmath: AMS mathematical facilities for LATEX
% amssymb: Defines all the symbols found in the AMS symbol fonts
% amsthm: Typesetting theorems (AMS style)
\RequirePackage{amsmath,amssymb,amsthm}
\RequirePackage{mathtools}
\theoremstyle{definition}
\newtheorem{definition}{Definition}
\newtheorem{example}{Example}
\newtheorem{exercise}{Exercise}
\newtheorem{property}{Property}
\newtheorem{question}{Question}
\newtheorem{solution}{Solution}

\theoremstyle{plain}
\newtheorem{theorem}{Theorem}
\newtheorem{proposition}{Proposition}
\newtheorem{problem}{Problem}
\newtheorem{lemma}{Lemma}
\newtheorem{conjecture}{Conjecture}
\newtheorem{corollary}{Corollary}
\newtheorem*{claim}{Claim}

\theoremstyle{remark}
\newtheorem{remark}{Remark}
\newtheorem{note}{Note}
\newtheorem{case}{Case}

\theoremstyle{plain}

% Floats and captions
\if@floatrow
  \RequirePackage{floatrow}
  \floatsetup[table]{style=Plaintop}
  \RequirePackage{caption}
  \captionsetup{labelfont={sf,bf}}
\else
  \RequirePackage{float}
  \newcommand\fs@iacrabove{%
    % Swap \abovecaptionskip and \belowcaptionskip
    \addtolength\abovecaptionskip{-\belowcaptionskip}
    \addtolength\belowcaptionskip{\abovecaptionskip}
    \addtolength\abovecaptionskip{-\belowcaptionskip}
    \setlength\abovecaptionskip{-\abovecaptionskip}
    \fs@plaintop%
    \def\@fs@cfont{\sffamily\bfseries}}
  \newcommand\fs@iacrbelow{%
    \fs@plain%
    \def\@fs@cfont{\sffamily\bfseries}
  }
  \floatstyle{iacrabove}
  \restylefloat{table}
  \floatstyle{iacrbelow}
  \restylefloat{figure}
\fi

% Line # for submission
\newcommand\linenomathWithnumbersforAMS{%
  \ifLineNumbers
    \ifnum\interlinepenalty>-\linenopenaltypar
      \global\holdinginserts\thr@@
      \advance\interlinepenalty \linenopenalty
     \ifhmode                                   % v4.3
      \advance\predisplaypenalty \linenopenalty
     \fi
      \advance\interdisplaylinepenalty \linenopenalty
    \fi
  \fi
  \ignorespaces
}

\ifcsstring{@IACRversion}{submission}{
  % lineno: Line numbers on paragraphs
  \RequirePackage[mathlines]{lineno}
  \linenumbers
  \def\linenumberfont{\normalfont\tiny\sffamily\color{gray}}

  % Taken from http://phaseportrait.blogspot.fr/2007/08/lineno-and-amsmath-compatibility.html
  \newcommand*\patchAmsMathEnvironmentForLineno[1]{%
    \expandafter\let\csname old#1\expandafter\endcsname\csname #1\endcsname
    \expandafter\let\csname oldend#1\expandafter\endcsname\csname end#1\endcsname
    \renewenvironment{#1}%
       {\linenomathWithnumbersforAMS\csname old#1\endcsname}%
       {\csname oldend#1\endcsname\endlinenomath}}%
  \newcommand*\patchBothAmsMathEnvironmentsForLineno[1]{%
    \patchAmsMathEnvironmentForLineno{#1}%
    \patchAmsMathEnvironmentForLineno{#1*}}%
  \AtBeginDocument{%
  \patchAmsMathEnvironmentForLineno{equation*}%
  \patchBothAmsMathEnvironmentsForLineno{align}%
  \patchBothAmsMathEnvironmentsForLineno{flalign}%
  \patchBothAmsMathEnvironmentsForLineno{alignat}%
  \patchBothAmsMathEnvironmentsForLineno{gather}%
  \patchBothAmsMathEnvironmentsForLineno{multline}%
  }
}{} %submission

% Microtype: Subliminal refinements towards typographical perfection
\RequirePackage{microtype}

% The Latin Modern family of fonts consists of 72 text fonts and 20 mathematics fonts
\RequirePackage{lmodern}

% Store the default font family used
\let\store@font\familydefault%

% Store the paper width
\let\store@paperwidth\paperwidth%

\endinput
%end of file iacrcc.cls
