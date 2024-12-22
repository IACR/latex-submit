"""This is a map from three-letter ISO codes to the name and two-letter iso code.
"""
iso_codes = {
 # two special cases.
 "eue": {
     "name": "European Union",
     "code": "eu"
 },
 "ooo": {
    "name": "Odarn",
    "code": "oo"
  },
  "afg": {
    "name": "Afghanistan",
    "code": "af"
  },
  "alb": {
    "name": "Albania",
    "code": "al"
  },
  "dza": {
    "name": "Algeria",
    "code": "dz"
  },
  "asm": {
    "name": "American Samoa",
    "code": "as"
  },
  "and": {
    "name": "Andorra",
    "code": "ad"
  },
  "ago": {
    "name": "Angola",
    "code": "ao"
  },
  "aia": {
    "name": "Anguilla",
    "code": "ai"
  },
  "ata": {
    "name": "Antarctica",
    "code": "aq"
  },
  "atg": {
    "name": "Antigua and Barbuda",
    "code": "ag"
  },
  "arg": {
    "name": "Argentina",
    "code": "ar"
  },
  "arm": {
    "name": "Armenia",
    "code": "am"
  },
  "abw": {
    "name": "Aruba",
    "code": "aw"
  },
  "aus": {
    "name": "Australia",
    "code": "au"
  },
  "aut": {
    "name": "Austria",
    "code": "at"
  },
  "aze": {
    "name": "Azerbaijan",
    "code": "az"
  },
  "bhs": {
    "name": "Bahamas",
    "code": "bs"
  },
  "bhr": {
    "name": "Bahrain",
    "code": "bh"
  },
  "bgd": {
    "name": "Bangladesh",
    "code": "bd"
  },
  "brb": {
    "name": "Barbados",
    "code": "bb"
  },
  "blr": {
    "name": "Belarus",
    "code": "by"
  },
  "bel": {
    "name": "Belgium",
    "code": "be"
  },
  "blz": {
    "name": "Belize",
    "code": "bz"
  },
  "ben": {
    "name": "Benin",
    "code": "bj"
  },
  "bmu": {
    "name": "Bermuda",
    "code": "bm"
  },
  "btn": {
    "name": "Bhutan",
    "code": "bt"
  },
  "bol": {
    "name": "Bolivia",
    "code": "bo"
  },
  "bes": {
    "name": "Bonaire, Sint Eustatius and Saba",
    "code": "bq"
  },
  "bih": {
    "name": "Bosnia and Herzegovina",
    "code": "ba"
  },
  "bwa": {
    "name": "Botswana",
    "code": "bw"
  },
  "bvt": {
    "name": "Bouvet Island",
    "code": "bv"
  },
  "bra": {
    "name": "Brazil",
    "code": "br"
  },
  "iot": {
    "name": "British Indian Ocean Territory",
    "code": "io"
  },
  "vgb": {
    "name": "British Virgin Islands",
    "code": "vg"
  },
  "brn": {
    "name": "Brunei Darussalam",
    "code": "bn"
  },
  "bgr": {
    "name": "Bulgaria",
    "code": "bg"
  },
  "bfa": {
    "name": "Burkina Faso",
    "code": "bf"
  },
  "bdi": {
    "name": "Burundi",
    "code": "bi"
  },
  "cpv": {
    "name": "Cabo Verde",
    "code": "cv"
  },
  "khm": {
    "name": "Cambodia",
    "code": "kh"
  },
  "cmr": {
    "name": "Cameroon",
    "code": "cm"
  },
  "can": {
    "name": "Canada",
    "code": "ca"
  },
  "cym": {
    "name": "Cayman Islands",
    "code": "ky"
  },
  "caf": {
    "name": "Central African Republic",
    "code": "cf"
  },
  "tcd": {
    "name": "Chad",
    "code": "td"
  },
  "chl": {
    "name": "Chile",
    "code": "cl"
  },
  "chn": {
    "name": "China",
    "code": "cn"
  },
  "cxr": {
    "name": "Christmas Island",
    "code": "cx"
  },
  "cck": {
    "name": "Cocos (Keeling) Islands",
    "code": "cc"
  },
  "col": {
    "name": "Colombia",
    "code": "co"
  },
  "com": {
    "name": "Comoros",
    "code": "km"
  },
  "cog": {
    "name": "Congo",
    "code": "cg"
  },
  "cok": {
    "name": "Cook Islands",
    "code": "ck"
  },
  "cri": {
    "name": "Costa Rica",
    "code": "cr"
  },
  "hrv": {
    "name": "Croatia",
    "code": "hr"
  },
  "cub": {
    "name": "Cuba",
    "code": "cu"
  },
  "cuw": {
    "name": "Cura\u00e7ao",
    "code": "cw"
  },
  "cyp": {
    "name": "Cyprus",
    "code": "cy"
  },
  "cze": {
    "name": "Czechia",
    "code": "cz"
  },
  "civ": {
    "name": "C\u00f4te d'Ivoire",
    "code": "ci"
  },
  "prk": {
    "name": "Democratic People's Republic of Korea",
    "code": "kp"
  },
  "cod": {
    "name": "Democratic Republic of Congo",
    "code": "cd"
  },
  "dnk": {
    "name": "Denmark",
    "code": "dk"
  },
  "dji": {
    "name": "Djibouti",
    "code": "dj"
  },
  "dma": {
    "name": "Dominica",
    "code": "dm"
  },
  "dom": {
    "name": "Dominican Republic",
    "code": "do"
  },
  "ecu": {
    "name": "Ecuador",
    "code": "ec"
  },
  "egy": {
    "name": "Egypt",
    "code": "eg"
  },
  "slv": {
    "name": "El Salvador",
    "code": "sv"
  },
  "gnq": {
    "name": "Equatorial Guinea",
    "code": "gq"
  },
  "eri": {
    "name": "Eritrea",
    "code": "er"
  },
  "est": {
    "name": "Estonia",
    "code": "ee"
  },
  "eth": {
    "name": "Ethiopia",
    "code": "et"
  },
  "flk": {
    "name": "Falkland Islands",
    "code": "fk"
  },
  "fro": {
    "name": "Faroe Islands",
    "code": "fo"
  },
  "fji": {
    "name": "Fiji",
    "code": "fj"
  },
  "fin": {
    "name": "Finland",
    "code": "fi"
  },
  "fra": {
    "name": "France",
    "code": "fr"
  },
  "guf": {
    "name": "French Guiana",
    "code": "gf"
  },
  "pyf": {
    "name": "French Polynesia",
    "code": "pf"
  },
  "atf": {
    "name": "French Southern Territories",
    "code": "tf"
  },
  "gab": {
    "name": "Gabon",
    "code": "ga"
  },
  "gmb": {
    "name": "Gambia",
    "code": "gm"
  },
  "geo": {
    "name": "Georgia",
    "code": "ge"
  },
  "deu": {
    "name": "Germany",
    "code": "de"
  },
  "gha": {
    "name": "Ghana",
    "code": "gh"
  },
  "gib": {
    "name": "Gibraltar",
    "code": "gi"
  },
  "grc": {
    "name": "Greece",
    "code": "gr"
  },
  "grl": {
    "name": "Greenland",
    "code": "gl"
  },
  "grd": {
    "name": "Grenada",
    "code": "gd"
  },
  "glp": {
    "name": "Guadeloupe",
    "code": "gp"
  },
  "gum": {
    "name": "Guam",
    "code": "gu"
  },
  "gtm": {
    "name": "Guatemala",
    "code": "gt"
  },
  "ggy": {
    "name": "Guernsey",
    "code": "gg"
  },
  "gin": {
    "name": "Guinea",
    "code": "gn"
  },
  "gnb": {
    "name": "Guinea-Bissau",
    "code": "gw"
  },
  "guy": {
    "name": "Guyana",
    "code": "gy"
  },
  "hti": {
    "name": "Haiti",
    "code": "ht"
  },
  "hmd": {
    "name": "Heard Island and McDonald Islands",
    "code": "hm"
  },
  "hnd": {
    "name": "Honduras",
    "code": "hn"
  },
  "hkg": {
    "name": "Hong Kong",
    "code": "hk"
  },
  "hun": {
    "name": "Hungary",
    "code": "hu"
  },
  "isl": {
    "name": "Iceland",
    "code": "is"
  },
  "ind": {
    "name": "India",
    "code": "in"
  },
  "idn": {
    "name": "Indonesia",
    "code": "id"
  },
  "irn": {
    "name": "Iran",
    "code": "ir"
  },
  "irq": {
    "name": "Iraq",
    "code": "iq"
  },
  "irl": {
    "name": "Ireland",
    "code": "ie"
  },
  "imn": {
    "name": "Isle of Man",
    "code": "im"
  },
  "isr": {
    "name": "Israel",
    "code": "il"
  },
  "ita": {
    "name": "Italy",
    "code": "it"
  },
  "jam": {
    "name": "Jamaica",
    "code": "jm"
  },
  "jpn": {
    "name": "Japan",
    "code": "jp"
  },
  "jey": {
    "name": "Jersey",
    "code": "je"
  },
  "jor": {
    "name": "Jordan",
    "code": "jo"
  },
  "kaz": {
    "name": "Kazakhstan",
    "code": "kz"
  },
  "ken": {
    "name": "Kenya",
    "code": "ke"
  },
  "kir": {
    "name": "Kiribati",
    "code": "ki"
  },
  "kwt": {
    "name": "Kuwait",
    "code": "kw"
  },
  "kgz": {
    "name": "Kyrgyzstan",
    "code": "kg"
  },
  "lao": {
    "name": "Lao People's Democratic Republic",
    "code": "la"
  },
  "lva": {
    "name": "Latvia",
    "code": "lv"
  },
  "lbn": {
    "name": "Lebanon",
    "code": "lb"
  },
  "lso": {
    "name": "Lesotho",
    "code": "ls"
  },
  "lbr": {
    "name": "Liberia",
    "code": "lr"
  },
  "lby": {
    "name": "Libya",
    "code": "ly"
  },
  "lie": {
    "name": "Liechtenstein",
    "code": "li"
  },
  "ltu": {
    "name": "Lithuania",
    "code": "lt"
  },
  "lux": {
    "name": "Luxembourg",
    "code": "lu"
  },
  "mac": {
    "name": "Macao",
    "code": "mo"
  },
  "mkd": {
    "name": "Macedonia",
    "code": "mk"
  },
  "mdg": {
    "name": "Madagascar",
    "code": "mg"
  },
  "mwi": {
    "name": "Malawi",
    "code": "mw"
  },
  "mys": {
    "name": "Malaysia",
    "code": "my"
  },
  "mdv": {
    "name": "Maldives",
    "code": "mv"
  },
  "mli": {
    "name": "Mali",
    "code": "ml"
  },
  "mlt": {
    "name": "Malta",
    "code": "mt"
  },
  "mhl": {
    "name": "Marshall Islands",
    "code": "mh"
  },
  "mtq": {
    "name": "Martinique",
    "code": "mq"
  },
  "mrt": {
    "name": "Mauritania",
    "code": "mr"
  },
  "mus": {
    "name": "Mauritius",
    "code": "mu"
  },
  "myt": {
    "name": "Mayotte",
    "code": "yt"
  },
  "mex": {
    "name": "Mexico",
    "code": "mx"
  },
  "fsm": {
    "name": "Micronesia",
    "code": "fm"
  },
  "mda": {
    "name": "Moldova",
    "code": "md"
  },
  "mco": {
    "name": "Monaco",
    "code": "mc"
  },
  "mng": {
    "name": "Mongolia",
    "code": "mn"
  },
  "mne": {
    "name": "Montenegro",
    "code": "me"
  },
  "msr": {
    "name": "Montserrat",
    "code": "ms"
  },
  "mar": {
    "name": "Morocco",
    "code": "ma"
  },
  "moz": {
    "name": "Mozambique",
    "code": "mz"
  },
  "mmr": {
    "name": "Myanmar",
    "code": "mm"
  },
  "nam": {
    "name": "Namibia",
    "code": "na"
  },
  "nru": {
    "name": "Nauru",
    "code": "nr"
  },
  "npl": {
    "name": "Nepal",
    "code": "np"
  },
  "nld": {
    "name": "Netherlands",
    "code": "nl"
  },
  "ncl": {
    "name": "New Caledonia",
    "code": "nc"
  },
  "nzl": {
    "name": "New Zealand",
    "code": "nz"
  },
  "nic": {
    "name": "Nicaragua",
    "code": "ni"
  },
  "ner": {
    "name": "Niger",
    "code": "ne"
  },
  "nga": {
    "name": "Nigeria",
    "code": "ng"
  },
  "niu": {
    "name": "Niue",
    "code": "nu"
  },
  "nfk": {
    "name": "Norfolk Island",
    "code": "nf"
  },
  "mnp": {
    "name": "Northern Mariana Islands",
    "code": "mp"
  },
  "nor": {
    "name": "Norway",
    "code": "no"
  },
  "omn": {
    "name": "Oman",
    "code": "om"
  },
  "pak": {
    "name": "Pakistan",
    "code": "pk"
  },
  "plw": {
    "name": "Palau",
    "code": "pw"
  },
  "pse": {
    "name": "Palestine, State of",
    "code": "ps"
  },
  "pan": {
    "name": "Panama",
    "code": "pa"
  },
  "png": {
    "name": "Papua New Guinea",
    "code": "pg"
  },
  "pry": {
    "name": "Paraguay",
    "code": "py"
  },
  "per": {
    "name": "Peru",
    "code": "pe"
  },
  "phl": {
    "name": "Philippines",
    "code": "ph"
  },
  "pcn": {
    "name": "Pitcairn",
    "code": "pn"
  },
  "pol": {
    "name": "Poland",
    "code": "pl"
  },
  "prt": {
    "name": "Portugal",
    "code": "pt"
  },
  "pri": {
    "name": "Puerto Rico",
    "code": "pr"
  },
  "qat": {
    "name": "Qatar",
    "code": "qa"
  },
  "kor": {
    "name": "Republic of Korea",
    "code": "kr"
  },
  "rou": {
    "name": "Romania",
    "code": "ro"
  },
  "rus": {
    "name": "Russian Federation",
    "code": "ru"
  },
  "rwa": {
    "name": "Rwanda",
    "code": "rw"
  },
  "reu": {
    "name": "R\u00e9union",
    "code": "re"
  },
  "blm": {
    "name": "Saint Barth\u00e9lemy",
    "code": "bl"
  },
  "shn": {
    "name": "Saint Helena, Ascension and Tristan da Cunha",
    "code": "sh"
  },
  "kna": {
    "name": "Saint Kitts and Nevis",
    "code": "kn"
  },
  "lca": {
    "name": "Saint Lucia",
    "code": "lc"
  },
  "maf": {
    "name": "Saint Martin",
    "code": "mf"
  },
  "spm": {
    "name": "Saint Pierre and Miquelon",
    "code": "pm"
  },
  "vct": {
    "name": "Saint Vincent and the Grenadines",
    "code": "vc"
  },
  "wsm": {
    "name": "Samoa",
    "code": "ws"
  },
  "smr": {
    "name": "San Marino",
    "code": "sm"
  },
  "stp": {
    "name": "Sao Tome and Principe",
    "code": "st"
  },
  "sau": {
    "name": "Saudi Arabia",
    "code": "sa"
  },
  "sen": {
    "name": "Senegal",
    "code": "sn"
  },
  "srb": {
    "name": "Serbia",
    "code": "rs"
  },
  "syc": {
    "name": "Seychelles",
    "code": "sc"
  },
  "sle": {
    "name": "Sierra Leone",
    "code": "sl"
  },
  "sgp": {
    "name": "Singapore",
    "code": "sg"
  },
  "sxm": {
    "name": "Sint Maarten",
    "code": "sx"
  },
  "svk": {
    "name": "Slovakia",
    "code": "sk"
  },
  "svn": {
    "name": "Slovenia",
    "code": "si"
  },
  "slb": {
    "name": "Solomon Islands",
    "code": "sb"
  },
  "som": {
    "name": "Somalia",
    "code": "so"
  },
  "zaf": {
    "name": "South Africa",
    "code": "za"
  },
  "sgs": {
    "name": "South Georgia and the South Sandwich Islands",
    "code": "gs"
  },
  "ssd": {
    "name": "South Sudan",
    "code": "ss"
  },
  "esp": {
    "name": "Spain",
    "code": "es"
  },
  "lka": {
    "name": "Sri Lanka",
    "code": "lk"
  },
  "sdn": {
    "name": "Sudan",
    "code": "sd"
  },
  "sur": {
    "name": "Suriname",
    "code": "sr"
  },
  "sjm": {
    "name": "Svalbard and Jan Mayen",
    "code": "sj"
  },
  "swz": {
    "name": "Swaziland",
    "code": "sz"
  },
  "swe": {
    "name": "Sweden",
    "code": "se"
  },
  "che": {
    "name": "Switzerland",
    "code": "ch"
  },
  "syr": {
    "name": "Syrian Arab Republic",
    "code": "sy"
  },
  "twn": {
    "name": "Taiwan",
    "code": "tw"
  },
  "tjk": {
    "name": "Tajikistan",
    "code": "tj"
  },
  "tza": {
    "name": "Tanzania, United Republic of",
    "code": "tz"
  },
  "tha": {
    "name": "Thailand",
    "code": "th"
  },
  "tls": {
    "name": "Timor-Leste",
    "code": "tl"
  },
  "tgo": {
    "name": "Togo",
    "code": "tg"
  },
  "tkl": {
    "name": "Tokelau",
    "code": "tk"
  },
  "ton": {
    "name": "Tonga",
    "code": "to"
  },
  "tto": {
    "name": "Trinidad and Tobago",
    "code": "tt"
  },
  "tun": {
    "name": "Tunisia",
    "code": "tn"
  },
  "tur": {
    "name": "Turkey",
    "code": "tr"
  },
  "tkm": {
    "name": "Turkmenistan",
    "code": "tm"
  },
  "tca": {
    "name": "Turks and Caicos Islands",
    "code": "tc"
  },
  "tuv": {
    "name": "Tuvalu",
    "code": "tv"
  },
  "vir": {
    "name": "U.S. Virgin Islands",
    "code": "vi"
  },
  "uga": {
    "name": "Uganda",
    "code": "ug"
  },
  "ukr": {
    "name": "Ukraine",
    "code": "ua"
  },
  "are": {
    "name": "United Arab Emirates",
    "code": "ae"
  },
  "gbr": {
    "name": "United Kingdom of Great Britain and Northern Ireland",
    "code": "gb"
  },
  "umi": {
    "name": "United States Minor Outlying Islands",
    "code": "um"
  },
  "usa": {
    "name": "United States of America",
    "code": "us"
  },
  "ury": {
    "name": "Uruguay",
    "code": "uy"
  },
  "uzb": {
    "name": "Uzbekistan",
    "code": "uz"
  },
  "vut": {
    "name": "Vanuatu",
    "code": "vu"
  },
  "vat": {
    "name": "Vatican",
    "code": "va"
  },
  "ven": {
    "name": "Venezuela",
    "code": "ve"
  },
  "vnm": {
    "name": "Viet Nam",
    "code": "vn"
  },
  "wlf": {
    "name": "Wallis and Futuna",
    "code": "wf"
  },
  "esh": {
    "name": "Western Sahara*",
    "code": "eh"
  },
  "yem": {
    "name": "Yemen",
    "code": "ye"
  },
  "zmb": {
    "name": "Zambia",
    "code": "zm"
  },
  "zwe": {
    "name": "Zimbabwe",
    "code": "zw"
  },
  "ala": {
    "name": "\u00c5land Islands",
    "code": "ax"
  }
}
