"""This is a weak substitute for country_converter.  Unfortunately
country_converter depends upon pandas and cannot be used in a wsgi
app.
"""

import difflib

_country_data = {
    "aruba": "AW",
    "abw": "AW",
    "aw": "AW",
    "afghanistan": "AF",
    "afg": "AF",
    "af": "AF",
    "islamic republic of afghanistan": "AF",
    "angola": "AO",
    "ago": "AO",
    "ao": "AO",
    "republic of angola": "AO",
    "anguilla": "AI",
    "aia": "AI",
    "ai": "AI",
    "\u00e5land islands": "AX",
    "ala": "AX",
    "ax": "AX",
    "albania": "AL",
    "alb": "AL",
    "al": "AL",
    "republic of albania": "AL",
    "andorra": "AD",
    "and": "AD",
    "ad": "AD",
    "principality of andorra": "AD",
    "united arab emirates": "AE",
    "are": "AE",
    "ae": "AE",
    "argentina": "AR",
    "arg": "AR",
    "ar": "AR",
    "argentine republic": "AR",
    "armenia": "AM",
    "arm": "AM",
    "am": "AM",
    "republic of armenia": "AM",
    "american samoa": "AS",
    "asm": "AS",
    "as": "AS",
    "antarctica": "AQ",
    "ata": "AQ",
    "aq": "AQ",
    "french southern territories": "TF",
    "atf": "TF",
    "tf": "TF",
    "antigua and barbuda": "AG",
    "atg": "AG",
    "ag": "AG",
    "australia": "AU",
    "aus": "AU",
    "au": "AU",
    "austria": "AT",
    "aut": "AT",
    "at": "AT",
    "republic of austria": "AT",
    "azerbaijan": "AZ",
    "aze": "AZ",
    "az": "AZ",
    "republic of azerbaijan": "AZ",
    "burundi": "BI",
    "bdi": "BI",
    "bi": "BI",
    "republic of burundi": "BI",
    "belgium": "BE",
    "bel": "BE",
    "be": "BE",
    "british antarctic territories": "B1",
    "kingdom of belgium": "BE",
    "kosovo": "XK",
    "benin": "BJ",
    "ben": "BJ",
    "bj": "BJ",
    "republic of benin": "BJ",
    "bonaire, sint eustatius and saba": "BQ",
    "bes": "BQ",
    "bq": "BQ",
    "burkina faso": "BF",
    "bfa": "BF",
    "bf": "BF",
    "bangladesh": "BD",
    "bgd": "BD",
    "bd": "BD",
    "people\"s republic of bangladesh": "BD",
    "bulgaria": "BG",
    "bgr": "BG",
    "bg": "BG",
    "republic of bulgaria": "BG",
    "bahrain": "BH",
    "bhr": "BH",
    "bh": "BH",
    "kingdom of bahrain": "BH",
    "bahamas": "BS",
    "bhs": "BS",
    "bs": "BS",
    "commonwealth of the bahamas": "BS",
    "bosnia and herzegovina": "BA",
    "bih": "BA",
    "ba": "BA",
    "republic of bosnia and herzegovina": "BA",
    "saint barth\u00e9lemy": "BL",
    "st. helena": "SH",
    "st helena": "SH",
    "blm": "BL",
    "bl": "BL",
    "belarus": "BY",
    "blr": "BY",
    "by": "BY",
    "republic of belarus": "BY",
    "belize": "BZ",
    "blz": "BZ",
    "bz": "BZ",
    "bermuda": "BM",
    "bmu": "BM",
    "bm": "BM",
    "bolivia, plurinational state of": "BO",
    "bol": "BO",
    "bo": "BO",
    "plurinational state of bolivia": "BO",
    "bolivia": "BO",
    "brazil": "BR",
    "bra": "BR",
    "br": "BR",
    "federative republic of brazil": "BR",
    "barbados": "BB",
    "brb": "BB",
    "bb": "BB",
    "brunei darussalam": "BN",
    "brn": "BN",
    "bn": "BN",
    "bhutan": "BT",
    "btn": "BT",
    "bt": "BT",
    "kingdom of bhutan": "BT",
    "bouvet island": "BV",
    "bvt": "BV",
    "bv": "BV",
    "botswana": "BW",
    "bwa": "BW",
    "bw": "BW",
    "republic of botswana": "BW",
    "central african republic": "CF",
    "caf": "CF",
    "cf": "CF",
    "canada": "CA",
    "can": "CA",
    "ca": "CA",
    "cocos islands": "CC",
    "keeling islands": "CC",
    "cck": "CC",
    "cc": "CC",
    "switzerland": "CH",
    "suisse": "CH",
    "schweiz": "CH",
    "che": "CH",
    "ch": "CH",
    "swiss confederation": "CH",
    "chile": "CL",
    "chl": "CL",
    "cl": "CL",
    "republic of chile": "CL",
    "china": "CN",
    "chn": "CN",
    "cn": "CN",
    "people's republic of china": "CN",
    "c\u00f4te d'ivoire": "CI",
    "civ": "CI",
    "ci": "CI",
    "republic of c\u00f4te d'ivoire": "CI",
    "cameroon": "CM",
    "cmr": "CM",
    "cm": "CM",
    "republic of cameroon": "CM",
    "congo, the democratic republic of the": "CD",
    "dr congo": "CD",
    "congo republic": "CG",
    "congo-brazzaville": "CG",
    "cod": "CD",
    "cd": "CD",
    "congo": "CG",
    "cog": "CG",
    "cg": "CG",
    "republic of the congo": "CG",
    "cook islands": "CK",
    "cok": "CK",
    "ck": "CK",
    "colombia": "CO",
    "col": "CO",
    "co": "CO",
    "republic of colombia": "CO",
    "comoros": "KM",
    "com": "KM",
    "km": "KM",
    "union of the comoros": "KM",
    "cabo verde": "CV",
    "cpv": "CV",
    "cv": "CV",
    "republic of cabo verde": "CV",
    "costa rica": "CR",
    "cri": "CR",
    "cr": "CR",
    "republic of costa rica": "CR",
    "cuba": "CU",
    "cub": "CU",
    "cu": "CU",
    "republic of cuba": "CU",
    "cura\u00e7ao": "CW",
    "cuw": "CW",
    "cw": "CW",
    "christmas island": "CX",
    "cxr": "CX",
    "cx": "CX",
    "cayman islands": "KY",
    "cym": "KY",
    "ky": "KY",
    "cyprus": "CY",
    "cyp": "CY",
    "cy": "CY",
    "republic of cyprus": "CY",
    "czechia": "CZ",
    "cze": "CZ",
    "cz": "CZ",
    "czech republic": "CZ",
    "germany": "DE",
    "deutschland": "DE",
    "deu": "DE",
    "de": "DE",
    "federal republic of germany": "DE",
    "djibouti": "DJ",
    "dji": "DJ",
    "dj": "DJ",
    "republic of djibouti": "DJ",
    "dominica": "DM",
    "dma": "DM",
    "dm": "DM",
    "commonwealth of dominica": "DM",
    "denmark": "DK",
    "dnk": "DK",
    "dk": "DK",
    "kingdom of denmark": "DK",
    "dominican republic": "DO",
    "dom": "DO",
    "do": "DO",
    "algeria": "DZ",
    "dza": "DZ",
    "dz": "DZ",
    "people's democratic republic of algeria": "DZ",
    "ecuador": "EC",
    "ecu": "EC",
    "ec": "EC",
    "republic of ecuador": "EC",
    "egypt": "EG",
    "egy": "EG",
    "eg": "EG",
    "arab republic of egypt": "EG",
    "eritrea": "ER",
    "eri": "ER",
    "er": "ER",
    "the state of eritrea": "ER",
    "western sahara": "EH",
    "esh": "EH",
    "eh": "EH",
    "spain": "ES",
    "esp": "ES",
    "es": "ES",
    "kingdom of spain": "ES",
    "estonia": "EE",
    "est": "EE",
    "ee": "EE",
    "republic of estonia": "EE",
    "ethiopia": "ET",
    "eth": "ET",
    "et": "ET",
    "federal democratic republic of ethiopia": "ET",
    "finland": "FI",
    "fin": "FI",
    "fi": "FI",
    "republic of finland": "FI",
    "fiji": "FJ",
    "fji": "FJ",
    "fj": "FJ",
    "republic of fiji": "FJ",
    "malvinas": "FK",
    "falkland islands": "FK",
    "flk": "FK",
    "fk": "FK",
    "france": "FR",
    "fra": "FR",
    "fr": "FR",
    "french republic": "FR",
    "faroe islands": "FO",
    "fro": "FO",
    "fo": "FO",
    "micronesia, federated states of": "FM",
    "fsm": "FM",
    "fm": "FM",
    "federated states of micronesia": "FM",
    "gabon": "GA",
    "gab": "GA",
    "ga": "GA",
    "gabonese republic": "GA",
    "united kingdom": "GB",
    "gbr": "GB",
    "gb": "GB",
    "united kingdom of great britain and northern ireland": "GB",
    "georgia": "GE",
    "geo": "GE",
    "ge": "GE",
    "guernsey": "GG",
    "ggy": "GG",
    "gg": "GG",
    "ghana": "GH",
    "gha": "GH",
    "gh": "GH",
    "republic of ghana": "GH",
    "gibraltar": "GI",
    "gib": "GI",
    "gi": "GI",
    "guinea": "GN",
    "gin": "GN",
    "gn": "GN",
    "republic of guinea": "GN",
    "guadeloupe": "GP",
    "glp": "GP",
    "gp": "GP",
    "gambia": "GM",
    "gmb": "GM",
    "gm": "GM",
    "republic of the gambia": "GM",
    "guinea-bissau": "GW",
    "gnb": "GW",
    "gw": "GW",
    "republic of guinea-bissau": "GW",
    "equatorial guinea": "GQ",
    "gnq": "GQ",
    "gq": "GQ",
    "republic of equatorial guinea": "GQ",
    "greece": "GR",
    "grc": "GR",
    "gr": "GR",
    "hellenic republic": "GR",
    "grenada": "GD",
    "grd": "GD",
    "gd": "GD",
    "greenland": "GL",
    "grl": "GL",
    "gl": "GL",
    "guatemala": "GT",
    "gtm": "GT",
    "gt": "GT",
    "republic of guatemala": "GT",
    "french guiana": "GF",
    "guf": "GF",
    "gf": "GF",
    "guam": "GU",
    "gum": "GU",
    "gu": "GU",
    "guyana": "GY",
    "guy": "GY",
    "gy": "GY",
    "republic of guyana": "GY",
    "hong kong": "HK",
    "hkg": "HK",
    "hk": "HK",
    "hong kong special administrative region of china": "HK",
    "heard island and mcdonald islands": "HM",
    "hmd": "HM",
    "hm": "HM",
    "honduras": "HN",
    "hnd": "HN",
    "hn": "HN",
    "republic of honduras": "HN",
    "croatia": "HR",
    "hrv": "HR",
    "hr": "HR",
    "republic of croatia": "HR",
    "haiti": "HT",
    "hti": "HT",
    "ht": "HT",
    "republic of haiti": "HT",
    "hungary": "HU",
    "hun": "HU",
    "hu": "HU",
    "indonesia": "ID",
    "idn": "ID",
    "id": "ID",
    "republic of indonesia": "ID",
    "isle of man": "IM",
    "imn": "IM",
    "im": "IM",
    "india": "IN",
    "ind": "IN",
    "in": "IN",
    "republic of india": "IN",
    "british indian ocean territory": "IO",
    "iot": "IO",
    "io": "IO",
    "ireland": "IE",
    "irl": "IE",
    "ie": "IE",
    "iran, islamic republic of": "IR",
    "irn": "IR",
    "ir": "IR",
    "islamic republic of iran": "IR",
    "iraq": "IQ",
    "irq": "IQ",
    "iq": "IQ",
    "republic of iraq": "IQ",
    "iceland": "IS",
    "isl": "IS",
    "is": "IS",
    "republic of iceland": "IS",
    "israel": "IL",
    "isr": "IL",
    "il": "IL",
    "state of israel": "IL",
    "italy": "IT",
    "ita": "IT",
    "it": "IT",
    "italian republic": "IT",
    "jamaica": "JM",
    "jam": "JM",
    "jm": "JM",
    "jersey": "JE",
    "jey": "JE",
    "je": "JE",
    "jordan": "JO",
    "jor": "JO",
    "jo": "JO",
    "hashemite kingdom of jordan": "JO",
    "japan": "JP",
    "jpn": "JP",
    "jp": "JP",
    "kazakhstan": "KZ",
    "kaz": "KZ",
    "kz": "KZ",
    "republic of kazakhstan": "KZ",
    "kenya": "KE",
    "ken": "KE",
    "ke": "KE",
    "republic of kenya": "KE",
    "kyrgyzstan": "KG",
    "kgz": "KG",
    "kg": "KG",
    "kyrgyz republic": "KG",
    "cambodia": "KH",
    "khm": "KH",
    "kh": "KH",
    "kingdom of cambodia": "KH",
    "kiribati": "KI",
    "kir": "KI",
    "ki": "KI",
    "republic of kiribati": "KI",
    "saint kitts and nevis": "KN",
    "kna": "KN",
    "kn": "KN",
    "korea, republic of": "KR",
    "kor": "KR",
    "kr": "KR",
    "south korea": "KR",
    "kuwait": "KW",
    "kwt": "KW",
    "kw": "KW",
    "state of kuwait": "KW",
    "lao people's democratic republic": "LA",
    "lao": "LA",
    "la": "LA",
    "lebanon": "LB",
    "lbn": "LB",
    "lb": "LB",
    "lebanese republic": "LB",
    "liberia": "LR",
    "lbr": "LR",
    "lr": "LR",
    "republic of liberia": "LR",
    "libya": "LY",
    "lby": "LY",
    "ly": "LY",
    "saint lucia": "LC",
    "lca": "LC",
    "lc": "LC",
    "liechtenstein": "LI",
    "lie": "LI",
    "li": "LI",
    "principality of liechtenstein": "LI",
    "sri lanka": "LK",
    "lka": "LK",
    "lk": "LK",
    "democratic socialist republic of sri lanka": "LK",
    "lesotho": "LS",
    "lso": "LS",
    "ls": "LS",
    "kingdom of lesotho": "LS",
    "lithuania": "LT",
    "ltu": "LT",
    "lt": "LT",
    "republic of lithuania": "LT",
    "luxembourg": "LU",
    "lux": "LU",
    "lu": "LU",
    "grand duchy of luxembourg": "LU",
    "latvia": "LV",
    "lva": "LV",
    "lv": "LV",
    "republic of latvia": "LV",
    "macao": "MO",
    "mac": "MO",
    "mo": "MO",
    "macao special administrative region of china": "MO",
    "saint martin": "MF",
    "saint-martin": "MF",
    "maf": "MF",
    "mf": "MF",
    "morocco": "MA",
    "mar": "MA",
    "ma": "MA",
    "kingdom of morocco": "MA",
    "monaco": "MC",
    "mco": "MC",
    "mc": "MC",
    "principality of monaco": "MC",
    "moldova, republic of": "MD",
    "mda": "MD",
    "md": "MD",
    "republic of moldova": "MD",
    "moldova": "MD",
    "madagascar": "MG",
    "mdg": "MG",
    "mg": "MG",
    "republic of madagascar": "MG",
    "maldives": "MV",
    "mdv": "MV",
    "mv": "MV",
    "republic of maldives": "MV",
    "mexico": "MX",
    "mex": "MX",
    "mx": "MX",
    "united mexican states": "MX",
    "marshall islands": "MH",
    "mhl": "MH",
    "mh": "MH",
    "republic of the marshall islands": "MH",
    "north macedonia": "MK",
    "mkd": "MK",
    "mk": "MK",
    "republic of north macedonia": "MK",
    "mali": "ML",
    "mli": "ML",
    "ml": "ML",
    "republic of mali": "ML",
    "malta": "MT",
    "mlt": "MT",
    "mt": "MT",
    "republic of malta": "MT",
    "myanmar": "MM",
    "mmr": "MM",
    "mm": "MM",
    "republic of myanmar": "MM",
    "montenegro": "ME",
    "mne": "ME",
    "me": "ME",
    "mongolia": "MN",
    "mng": "MN",
    "mn": "MN",
    "northern mariana islands": "MP",
    "mnp": "MP",
    "mp": "MP",
    "commonwealth of the northern mariana islands": "MP",
    "mozambique": "MZ",
    "moz": "MZ",
    "mz": "MZ",
    "republic of mozambique": "MZ",
    "mauritania": "MR",
    "mrt": "MR",
    "mr": "MR",
    "islamic republic of mauritania": "MR",
    "montserrat": "MS",
    "msr": "MS",
    "ms": "MS",
    "martinique": "MQ",
    "mtq": "MQ",
    "mq": "MQ",
    "mauritius": "MU",
    "mus": "MU",
    "mu": "MU",
    "republic of mauritius": "MU",
    "malawi": "MW",
    "mwi": "MW",
    "mw": "MW",
    "republic of malawi": "MW",
    "malaysia": "MY",
    "mys": "MY",
    "my": "MY",
    "mayotte": "YT",
    "myt": "YT",
    "yt": "YT",
    "namibia": "NA",
    "nam": "NA",
    "na": "NA",
    "republic of namibia": "NA",
    "new caledonia": "NC",
    "ncl": "NC",
    "nc": "NC",
    "niger": "NE",
    "ner": "NE",
    "ne": "NE",
    "republic of the niger": "NE",
    "norfolk island": "NF",
    "nfk": "NF",
    "nf": "NF",
    "nigeria": "NG",
    "nga": "NG",
    "ng": "NG",
    "federal republic of nigeria": "NG",
    "nicaragua": "NI",
    "nic": "NI",
    "ni": "NI",
    "republic of nicaragua": "NI",
    "niue": "NU",
    "niu": "NU",
    "nu": "NU",
    "netherlands": "NL",
    "netherlands antilles": "AN",
    "nld": "NL",
    "nl": "NL",
    "kingdom of the netherlands": "NL",
    "norway": "NO",
    "nor": "NO",
    "no": "NO",
    "kingdom of norway": "NO",
    "nepal": "NP",
    "npl": "NP",
    "np": "NP",
    "federal democratic republic of nepal": "NP",
    "nauru": "NR",
    "nru": "NR",
    "nr": "NR",
    "republic of nauru": "NR",
    "new zealand": "NZ",
    "nzl": "NZ",
    "nz": "NZ",
    "oman": "OM",
    "omn": "OM",
    "om": "OM",
    "sultanate of oman": "OM",
    "pakistan": "PK",
    "pak": "PK",
    "pk": "PK",
    "islamic republic of pakistan": "PK",
    "panama": "PA",
    "pan": "PA",
    "pa": "PA",
    "republic of panama": "PA",
    "pitcairn": "PN",
    "pcn": "PN",
    "pn": "PN",
    "peru": "PE",
    "per": "PE",
    "pe": "PE",
    "republic of peru": "PE",
    "philippines": "PH",
    "phl": "PH",
    "ph": "PH",
    "republic of the philippines": "PH",
    "palau": "PW",
    "plw": "PW",
    "pw": "PW",
    "republic of palau": "PW",
    "papua new guinea": "PG",
    "png": "PG",
    "pg": "PG",
    "independent state of papua new guinea": "PG",
    "poland": "PL",
    "pol": "PL",
    "pl": "PL",
    "republic of poland": "PL",
    "puerto rico": "PR",
    "pri": "PR",
    "pr": "PR",
    "korea, democratic people's republic of": "KP",
    "prk": "KP",
    "kp": "KP",
    "democratic people's republic of korea": "KP",
    "north korea": "KP",
    "portugal": "PT",
    "prt": "PT",
    "pt": "PT",
    "portuguese republic": "PT",
    "paraguay": "PY",
    "pry": "PY",
    "py": "PY",
    "republic of paraguay": "PY",
    "palestine, state of": "PS",
    "pse": "PS",
    "ps": "PS",
    "the state of palestine": "PS",
    "french polynesia": "PF",
    "pyf": "PF",
    "pf": "PF",
    "qatar": "QA",
    "qat": "QA",
    "qa": "QA",
    "state of qatar": "QA",
    "r\u00e9union": "RE",
    "reu": "RE",
    "re": "RE",
    "romania": "RO",
    "rou": "RO",
    "ro": "RO",
    "russian federation": "RU",
    "russia": "RU",
    "rus": "RU",
    "ru": "RU",
    "rwanda": "RW",
    "rwa": "RW",
    "rw": "RW",
    "rwandese republic": "RW",
    "saudi arabia": "SA",
    "sau": "SA",
    "sa": "SA",
    "kingdom of saudi arabia": "SA",
    "sudan": "SD",
    "sdn": "SD",
    "sd": "SD",
    "republic of the sudan": "SD",
    "senegal": "SN",
    "sen": "SN",
    "sn": "SN",
    "republic of senegal": "SN",
    "singapore": "SG",
    "sgp": "SG",
    "sg": "SG",
    "republic of singapore": "SG",
    "south georgia and the south sandwich islands": "GS",
    "sgs": "GS",
    "gs": "GS",
    "saint helena, ascension and tristan da cunha": "SH",
    "shn": "SH",
    "sh": "SH",
    "svalbard and jan mayen": "SJ",
    "sjm": "SJ",
    "sj": "SJ",
    "solomon islands": "SB",
    "slb": "SB",
    "sb": "SB",
    "sierra leone": "SL",
    "sle": "SL",
    "sl": "SL",
    "republic of sierra leone": "SL",
    "el salvador": "SV",
    "slv": "SV",
    "sv": "SV",
    "republic of el salvador": "SV",
    "san marino": "SM",
    "smr": "SM",
    "sm": "SM",
    "republic of san marino": "SM",
    "somalia": "SO",
    "som": "SO",
    "so": "SO",
    "federal republic of somalia": "SO",
    "saint pierre and miquelon": "PM",
    "spm": "PM",
    "pm": "PM",
    "serbia": "RS",
    "srb": "RS",
    "rs": "RS",
    "republic of serbia": "RS",
    "south sudan": "SS",
    "ssd": "SS",
    "ss": "SS",
    "republic of south sudan": "SS",
    "sao tome and principe": "ST",
    "stp": "ST",
    "st": "ST",
    "democratic republic of sao tome and principe": "ST",
    "suriname": "SR",
    "sur": "SR",
    "sr": "SR",
    "republic of suriname": "SR",
    "slovakia": "SK",
    "svk": "SK",
    "sk": "SK",
    "slovak republic": "SK",
    "slovenia": "SI",
    "svn": "SI",
    "si": "SI",
    "republic of slovenia": "SI",
    "sweden": "SE",
    "swe": "SE",
    "se": "SE",
    "kingdom of sweden": "SE",
    "eswatini": "SZ",
    "swz": "SZ",
    "sz": "SZ",
    "kingdom of eswatini": "SZ",
    "sint maarten": "SX",
    "sxm": "SX",
    "sx": "SX",
    "seychelles": "SC",
    "syc": "SC",
    "sc": "SC",
    "republic of seychelles": "SC",
    "syrian arab republic": "SY",
    "syr": "SY",
    "sy": "SY",
    "turks and caicos islands": "TC",
    "tca": "TC",
    "tc": "TC",
    "chad": "TD",
    "tcd": "TD",
    "td": "TD",
    "republic of chad": "TD",
    "togo": "TG",
    "tgo": "TG",
    "tg": "TG",
    "togolese republic": "TG",
    "thailand": "TH",
    "tha": "TH",
    "th": "TH",
    "kingdom of thailand": "TH",
    "tajikistan": "TJ",
    "tjk": "TJ",
    "tj": "TJ",
    "republic of tajikistan": "TJ",
    "tokelau": "TK",
    "tkl": "TK",
    "tk": "TK",
    "turkmenistan": "TM",
    "tkm": "TM",
    "tm": "TM",
    "timor-leste": "TL",
    "tls": "TL",
    "tl": "TL",
    "democratic republic of timor-leste": "TL",
    "tonga": "TO",
    "ton": "TO",
    "to": "TO",
    "kingdom of tonga": "TO",
    "trinidad and tobago": "TT",
    "tto": "TT",
    "tt": "TT",
    "republic of trinidad and tobago": "TT",
    "tunisia": "TN",
    "tun": "TN",
    "tn": "TN",
    "republic of tunisia": "TN",
    "turkey": "TR",
    "tur": "TR",
    "tr": "TR",
    "republic of turkey": "TR",
    "tuvalu": "TV",
    "tuv": "TV",
    "tv": "TV",
    "taiwan, province of china": "TW",
    "twn": "TW",
    "tw": "TW",
    "taiwan": "TW",
    "tanzania, united republic of": "TZ",
    "tza": "TZ",
    "tz": "TZ",
    "united republic of tanzania": "TZ",
    "tanzania": "TZ",
    "uganda": "UG",
    "uga": "UG",
    "ug": "UG",
    "republic of uganda": "UG",
    "ukraine": "UA",
    "ukr": "UA",
    "ua": "UA",
    "united states minor outlying islands": "UM",
    "umi": "UM",
    "um": "UM",
    "uruguay": "UY",
    "ury": "UY",
    "uy": "UY",
    "eastern republic of uruguay": "UY",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "united states of america": "US",
    "uzbekistan": "UZ",
    "uzb": "UZ",
    "uz": "UZ",
    "republic of uzbekistan": "UZ",
    "holy see": "VA",
    "vatican": "VA",
    "vatican city": "VA",
    "vat": "VA",
    "va": "VA",
    "saint vincent and the grenadines": "VC",
    "vct": "VC",
    "vc": "VC",
    "venezuela, bolivarian republic of": "VE",
    "ven": "VE",
    "ve": "VE",
    "bolivarian republic of venezuela": "VE",
    "venezuela": "VE",
    "virgin islands, british": "VG",
    "vgb": "VG",
    "vg": "VG",
    "british virgin islands": "VG",
    "virgin islands, u.s.": "VI",
    "united states virgin islands": "VI",
    "us virgin islands": "VI",
    "vir": "VI",
    "vi": "VI",
    "virgin islands of the united states": "VI",
    "viet nam": "VN",
    "vnm": "VN",
    "vn": "VN",
    "socialist republic of viet nam": "VN",
    "vietnam": "VN",
    "vanuatu": "VU",
    "vut": "VU",
    "vu": "VU",
    "republic of vanuatu": "VU",
    "wallis and futuna": "WF",
    "wlf": "WF",
    "wf": "WF",
    "samoa": "WS",
    "wsm": "WS",
    "ws": "WS",
    "independent state of samoa": "WS",
    "yemen": "YE",
    "yem": "YE",
    "ye": "YE",
    "republic of yemen": "YE",
    "south africa": "ZA",
    "zaf": "ZA",
    "za": "ZA",
    "republic of south africa": "ZA",
    "zambia": "ZM",
    "zmb": "ZM",
    "zm": "ZM",
    "republic of zambia": "ZM",
    "zimbabwe": "ZW",
    "zwe": "ZW",
    "zw": "ZW",
    "republic of zimbabwe": "ZW"
}

def country_lookup(name):
    closest = difflib.get_close_matches(name.lower(), _country_data.keys(), n=1)
    if closest:
        return _country_data.get(closest[0])
    return None


