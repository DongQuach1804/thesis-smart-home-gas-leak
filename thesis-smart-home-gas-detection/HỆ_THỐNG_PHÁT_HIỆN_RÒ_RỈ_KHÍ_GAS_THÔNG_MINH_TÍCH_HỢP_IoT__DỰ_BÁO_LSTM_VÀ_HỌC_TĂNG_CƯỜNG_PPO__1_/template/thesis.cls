\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{template/thesis}[2024/04/16 v2.0.0 UIT Thesis Template by LuanVT]
\LoadClass[12pt,a4paper]{report}

% Core packages
\RequirePackage{iftex}
\ifPDFTeX
  \RequirePackage[utf8]{inputenc}
  \RequirePackage[T1,T5]{fontenc}
  \RequirePackage{mathptmx}
\else
  \RequirePackage{fontspec}
  \IfFontExistsTF{Times New Roman}
    {\setmainfont{Times New Roman}}
    {\setmainfont{TeX Gyre Termes}}
  \IfFontExistsTF{Arial}
    {\setsansfont{Arial}}
    {\setsansfont{TeX Gyre Heros}}
  \IfFontExistsTF{Consolas}
    {\setmonofont{Consolas}}
    {\setmonofont{Latin Modern Mono}}
\fi
\RequirePackage{anyfontsize}
\RequirePackage[fontsize=13pt]{scrextend}
\changefontsizes[19.5pt]{13pt}
% \RequirePackage[vietnamese,english]{babel}
% \RequirePackage{csquotes}
\RequirePackage{template/slashbox}
% \RequirePackage{microtype}

% Layout and headers
\RequirePackage{fancyhdr}
\RequirePackage{geometry}
\RequirePackage{setspace}
\RequirePackage{titlesec}
\RequirePackage[titles]{tocloft}

% Graphics and tables
\RequirePackage{graphicx}
\RequirePackage{caption,subcaption}
\RequirePackage{array,tabularx,booktabs,longtable}
\RequirePackage{multirow,makecell}
\RequirePackage{float}
\RequirePackage{ragged2e}

% Math packages
\RequirePackage{amsmath,amsfonts,amssymb,mathtools}
\RequirePackage{siunitx}
\RequirePackage[mathscr]{euscript}

% Miscellaneous
\RequirePackage{pifont,adforn}
\RequirePackage{algorithm}
\RequirePackage{tikz}
\usetikzlibrary{calc}
\RequirePackage{template/slashbox}
\RequirePackage{pdfpages}
\RequirePackage{ftnxtra}
\RequirePackage{xcolor}


\RequirePackage[
	colorlinks=true,
	pdfstartview=FitV,
	linkcolor=black,
	citecolor=blue,
	urlcolor=blue,
	breaklinks=true
]{hyperref}
\RequirePackage{cleveref}


\RequirePackage{multido}
\RequirePackage{etoolbox}

\RequirePackage{latexsym,bbm,rotating}
\RequirePackage{enumitem,hhline,stmaryrd,bussproofs,arydshln}
\usetikzlibrary{calc}
\RequirePackage{lipsum}
\RequirePackage{textcase}
\RequirePackage{ftnxtra}


\providecommand\phantomsection{}

\RequirePackage{array,booktabs,arydshln,xcolor}
\newcommand\VRule[1][\arrayrulewidth]{\vrule width #1}
\newcolumntype{L}[1]{>{\raggedright\let\newline\\\arraybackslash\hspace{0pt}}m{#1}}
\newcolumntype{C}[1]{>{\centering\let\newline\\\arraybackslash\hspace{0pt}}m{#1}}
\newcolumntype{R}[1]{>{\raggedleft\let\newline\\\arraybackslash\hspace{0pt}}m{#1}}

%\RequirePackage{showframe}
\renewcommand{\labelitemii}{$\diamond$}
\renewcommand\cftchappresnum{Chương }
\renewcommand\cftchapaftersnum{.}
\newlength\mylen
\settowidth\mylen{\bfseries\cftchappresnum\thechapter\ }
\addtolength{\cftchapnumwidth}{\mylen}


\setlength\headheight{32pt}

\RequirePackage{setspace}
\onehalfspacing

\titleformat{\chapter}[hang]
{\fontsize{14pt}{21pt}\selectfont\bfseries}{\cftchappresnum\thechapter.}{0.5em}{\centering\MakeTextUppercase}

\titlespacing{\chapter}{0in}{-23pt}{20pt}

\titleformat*{\section}{\fontsize{13pt}{19.5pt}\selectfont\bfseries}
\titleformat*{\subsection}{\fontsize{13pt}{19.5pt}\selectfont\bfseries}
\titleformat*{\subsubsection}{\fontsize{13pt}{19.5pt}\selectfont\bfseries}
\titleformat*{\paragraph}{\fontsize{13pt}{19.5pt}\selectfont\bfseries}
\titleformat*{\subparagraph}{\fontsize{13pt}{19.5pt}\selectfont\bfseries}

\geometry{
	a4paper,
	left=3.5cm,
	right=2cm,
	top=3cm,
	bottom=3.5cm
}


\RequirePackage{acro,tabularray}
\acsetup{
    list/template=tabularray
}
\input{abbrev}

\RequirePackage[style=ieee, maxcitenames=2, mincitenames=1, backend=biber,
sorting=nyt, bibencoding=utf8, natbib=true, maxbibnames=99]{biblatex}
\DefineBibliographyStrings{english}{andothers={và các cộng sự}}
\DefineBibliographyStrings{english}{and={và}}
%\DefineBibliographyStrings{english}{pages={trang}}
%\DefineBibliographyStrings{english}{in={trong}}
\addbibresource{bibliography.bib}

\captionsetup[figure]{name={Hình},labelsep=period}
\captionsetup[table]{name={Bảng},labelsep=period}

\renewcommand{\chaptername}{Chương}
\renewcommand{\contentsname}{Mục lục}
\renewcommand{\listtablename}{Danh mục bảng}
\renewcommand\listfigurename{Danh mục hình}
\renewcommand{\bibname}{Tài liệu tham khảo}
\newcommand{\abbrevname}{Danh mục từ viết tắt}

\overfullrule=0pt

\fancypagestyle{customfancy}
{
   \fancyhf{}
    \fancyfoot[C]{\thepage}
    \renewcommand{\headrulewidth}{0pt}
    \renewcommand{\footrulewidth}{0pt}
}

\fancypagestyle{frontmatter}
{
   \fancyhf{}
   \renewcommand{\headrulewidth}{0pt}
   \renewcommand{\footrulewidth}{0pt}
}

\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}


% //STY


\brokenpenalty=10000

%%%%%%%%%% Title Module %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\newcommand{\Title}[2][local]{
    \expandafter\def\csname Title#1\endcsname{#2}%
}
\newcommand{\@Title}[1][local]{
    \edef\currentValue{\csname Title#1\endcsname}%
    \currentValue
}
%%%%%%%%%% End Title Module %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\def\University#1{\gdef\@University{#1}}
\def\CollegeOrDept#1{\gdef\@CollegeOrDept{#1}}
\def\Faculty#1{\gdef\@Faculty{#1}}
\def\Degree#1{\gdef\@Degree{#1}}
\def\ThesisType#1{\gdef\@ThesisType{#1}}
\def\ThesisYear#1{\gdef\@ThesisYear{#1}}
\def\ThesisLocation#1{\gdef\@ThesisLocation{#1}}
\def\@Degree{CỬ NHÂN}
\def\@Major{MẠNG MÁY TÍNH VÀ TRUYỀN THÔNG}
\def\Major#1{\gdef\@Major{#1}}
\def\MajorCode#1{\gdef\@MajorCode{#1}}

%%%%%%%%%% Author module %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\def\Authors{}
\newcommand{\Author}[2]{%
    \listadd{\Authors}{#1}%
    \expandafter\def\csname authorId#1\endcsname{#2}%
}
\newcommand{\@Authors}[1][\\]{ % #1 is delimiter
    \def\concatenated{}%
    \renewcommand*{\do}[1]{\edef\concatenated{\concatenated ##1#1}}%
    \dolistloop{\Authors}%
    \concatenated%
}
\newcommand{\@AuthorsWithId}[1][\par]{ % #1 is delimiter
    \renewcommand*{\do}[1]{
        {##1 – \csname authorId##1\endcsname#1}
    }%
    \dolistloop{\Authors}%
}
%%%%%%%%%% End Author module %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%%%%%%% Supervisor Module %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\def\Supervisors{}
\newcommand{\Supervisor}[1]{%
    \listadd{\Supervisors}{#1}%
}

\newcommand{\@Supervisor}[1][\\]{ % #1 is delimiter
    \def\concatenated{}%
    \renewcommand*{\do}[1]{\edef\concatenated{\concatenated ##1#1}}%
    \dolistloop{\Supervisors}%
    \concatenated%
}
%%%%%%%%%% End Supervisor Module %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newif\iffigurespage
\newif\iftablespage
\figurespagetrue
\tablespagetrue


% ============================================================
% Cover page layout
% ============================================================

% Width of centered title blocks on cover pages
\newlength{\coverblockwidth}
\setlength{\coverblockwidth}{0.82\textwidth}

% Shift cover contents to visually align with the centered cover frame.
% The document geometry uses left=3.5cm and right=2cm, so normal \centering
% follows the text area and appears slightly shifted to the right.
\newlength{\covercentershift}
\setlength{\covercentershift}{-0.75cm}

% Balanced cover frame: same margin on left and right
\newcommand{\coverframe}{%
    \begin{tikzpicture}[remember picture, overlay]
      \draw[line width=1pt]
        ([xshift=2.4cm,yshift=-2.0cm]current page.north west)
        rectangle
        ([xshift=-2.4cm,yshift=2.0cm]current page.south east);
    \end{tikzpicture}%
}

\def\firsttitlep{
    \thispagestyle{empty}
    \vspace*{-1.2cm}

    \noindent\hspace*{\covercentershift}%
    \begin{minipage}[t][23.2cm][t]{\textwidth}
    \centering

        {\fontsize{14pt}{21pt}\selectfont\textbf{\@University}\par}
        {\fontsize{16pt}{24pt}\selectfont\textbf{\@CollegeOrDept}\par}
        {\fontsize{16pt}{24pt}\selectfont\textbf{\@Faculty}\par}

        \vspace*{1.6ex}

        \includegraphics[width=2.2cm]{img/logouit.png}\par

        \vspace*{2.4ex}

        {\fontsize{14pt}{21pt}\selectfont\textbf{\@Authors}\par}

        \vspace*{3.4ex}

        {\fontsize{16pt}{24pt}\selectfont\textbf{\@ThesisType}\par}

        \vspace*{1.5ex}

        % Tên khóa luận tiếng Việt
        {\fontsize{18pt}{23pt}\selectfont\bfseries
        \parbox{\coverblockwidth}{%
            \centering
            \MakeTextUppercase{\@Title}
        }\par}

        % Khoảng cách giữa tên tiếng Việt và tiếng Anh
        \vspace*{5ex}

        % Tên khóa luận tiếng Anh
        {\fontsize{15pt}{20pt}\selectfont\bfseries
        \parbox{\coverblockwidth}{%
            \centering
            \textcolor{red}{\@Title[en]}
        }\par}

        \vspace*{5ex}

        % Dòng ngành
        {\fontsize{14pt}{21pt}\selectfont\bfseries
        \parbox{0.9\coverblockwidth}{%
            \centering
            \MakeTextUppercase{\@Degree}~NGÀNH \MakeTextUppercase{\@Major}
        }\par}

        % Đẩy địa điểm xuống cuối khung
        \vfill

        {\fontsize{13pt}{19.5pt}\selectfont
        \textbf{\MakeTextUppercase{\@ThesisLocation}, \@ThesisYear}\par}

        \vspace*{0.05cm}

    \end{minipage}
    \newpage
}

\def\secondtitlep{
    \thispagestyle{empty}
    \vspace*{-1.2cm}

    \noindent\hspace*{\covercentershift}%
    \begin{minipage}[t][23.2cm][t]{\textwidth}
    \centering

        {\fontsize{14pt}{21pt}\selectfont\textbf{\@University}\par}
        {\fontsize{16pt}{24pt}\selectfont\textbf{\@CollegeOrDept}\par}
        {\fontsize{16pt}{24pt}\selectfont\textbf{\@Faculty}\par}

        \vspace*{1.6ex}

        \includegraphics[width=2.2cm]{img/logouit.png}\par

        \vspace*{2.4ex}

        {\fontsize{14pt}{21pt}\selectfont\textbf{\@AuthorsWithId}\par}

        \vspace*{3.2ex}

        {\fontsize{16pt}{24pt}\selectfont\textbf{\@ThesisType}\par}

        \vspace*{1.5ex}

        % Tên khóa luận tiếng Việt
        {\fontsize{18pt}{23pt}\selectfont\bfseries
        \parbox{\coverblockwidth}{%
            \centering
            \MakeTextUppercase{\@Title}
        }\par}

        % Khoảng cách giữa tên tiếng Việt và tiếng Anh
        \vspace*{5ex}

        % Tên khóa luận tiếng Anh
        {\fontsize{15pt}{20pt}\selectfont\bfseries
        \parbox{\coverblockwidth}{%
            \centering
            \textcolor{red}{\@Title[en]}
        }\par}

        \vspace*{5ex}

                % Dòng ngành
        {\fontsize{14pt}{21pt}\selectfont\bfseries
        \parbox{0.9\coverblockwidth}{%
            \centering
            \MakeTextUppercase{\@Degree}~NGÀNH \MakeTextUppercase{\@Major}
        }\par}

        \vspace*{4.2ex}

        {\fontsize{14pt}{21pt}\selectfont\textbf{GIẢNG VIÊN HƯỚNG DẪN}\par}

        \vspace*{0.8ex}

        {\fontsize{14pt}{21pt}\selectfont\textbf{\@Supervisor}\par}

        % Đẩy địa điểm xuống cuối khung
        \vfill

        {\fontsize{13pt}{19.5pt}\selectfont
        \textbf{\MakeTextUppercase{\@ThesisLocation}, \@ThesisYear}\par}

        \vspace*{0.05cm}

    \end{minipage}
    \newpage
}

\def\firstbeforepreface{
    \pagenumbering{gobble}
    \pagestyle{frontmatter}
    \coverframe
    \firsttitlep
    \cleardoublepage
}

\def\secondbeforepreface{
    \pagenumbering{gobble}
    \pagestyle{frontmatter}
    \coverframe
    \secondtitlep
    \cleardoublepage
}

\def\beforepreface{
    \pagenumbering{gobble}
    \pagestyle{frontmatter}
    \coverframe
    \firsttitlep
    \coverframe
    \secondtitlep
    \cleardoublepage
}


\def\prefacesection#1{
    \chapter*{#1}
    \addcontentsline{toc}{chapter}{#1}
}

\def\afterpreface{
    \pagestyle{frontmatter}

    \newpage
    \IfFileExists{chapters/council.tex}{%
        \phantomsection
        \addcontentsline{toc}{chapter}{Thông tin hội đồng chấm khóa luận tốt nghiệp}
        \thispagestyle{frontmatter}
        \input{chapters/council.tex}
        \thispagestyle{frontmatter}
        \newpage
    }{}

    \phantomsection
    \addcontentsline{toc}{chapter}{Lời cảm ơn}
    \thispagestyle{frontmatter}
    \input{chapters/ack.tex}
    \thispagestyle{frontmatter}

    \newpage
    \phantomsection
	\addcontentsline{toc}{chapter}{\contentsname}
    \thispagestyle{frontmatter}
	\tableofcontents
    \thispagestyle{frontmatter}

    \newpage
    \phantomsection
	\addcontentsline{toc}{chapter}{\listtablename}
    \thispagestyle{frontmatter}
    \iftablespage
        \listoftables
    \fi
    \thispagestyle{frontmatter}

    \newpage
    \phantomsection
	\addcontentsline{toc}{chapter}{\listfigurename}
    \thispagestyle{frontmatter}
    \iffigurespage
        \listoffigures
    \fi
    \thispagestyle{frontmatter}
    
    \newpage
    \phantomsection
    \addcontentsline{toc}{chapter}{\abbrevname}
    \thispagestyle{frontmatter}
    \acuseall
    \printacronyms[name=\abbrevname]
    \thispagestyle{frontmatter}
    
    \cleardoublepage
    \pagenumbering{arabic}
    \setcounter{page}{1}
    \pagestyle{customfancy}

    \phantomsection
    \addcontentsline{toc}{chapter}{Tóm tắt}
    \input{chapters/abstract.tex}
    \cleardoublepage
}


\let\@ldthebibliography\thebibliography
\renewcommand{\thebibliography}[1]{\newpage
                \@ldthebibliography{#1}
\addcontentsline{toc}{chapter}{\bibname}}

\def\@endpart{\vfil\newpage
              \if@twoside
               \if@openright
                \null
                \thispagestyle{plain}%
                \newpage
               \fi
              \fi
              \if@tempswa
                \twocolumn
              \fi}

\makeatletter  
%% Switch meanings of starred and unstarred macros
%% (see https://tex.stackexchange.com/a/278398/5001)
\newcommand{\XDeclarePairedDelimiter}[3]{%  "X" for "exchange"
  \expandafter\DeclarePairedDelimiter\csname RIGHT\string#1\endcsname{#2}{#3}%
  \newcommand#1{%
    \@ifstar{\csname RIGHT\string#1\endcsname}
            {\@ifnextchar[{\csname RIGHT\string#1\endcsname}
                          {\csname RIGHT\string#1\endcsname*}%
}}}
\makeatother
\let\norm\relax % undefine existing "\norm" macro
\XDeclarePairedDelimiter{\norm}{\lVert}{\rVert}

\setcounter{secnumdepth}{3}
\setcounter{tocdepth}{3}