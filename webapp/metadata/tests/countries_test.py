import pytest
import sys
sys.path.insert(0, '../')
from countries import country_lookup

def test_country_lookup():
    testcases = {'united states': 'US',
                 'united snakes': 'US',
                 'united states of america': 'US',
                 'the united states': 'US',
                 'usa': 'US',
                 'turkey': 'TR',
                 'the netherlands': 'NL',
                 'Belgium': 'BE',
                 'Belgique': 'BE',
                 'palestine': 'PS',
                 'Russia': 'RU',
                 'Ukraine': 'UA',
                 'Japan': 'JP',
                 'la suise': 'CH',
                 'Mexico': 'MX',
                 'Le Mexique': None,
                 'Singapour': 'SG',
                 'Switzerland': 'CH',
                 'Suisse': 'CH',
                 'Italia': 'IT',
                 'italie': 'IT',
                 'Italy': 'IT'}

    for t in testcases:
        l = country_lookup(t)
        assert l == testcases.get(t)
        assert "AF" == country_lookup("Afghanistan")
        assert "AX" == country_lookup("Aland Islands")
        assert "AL" == country_lookup("Albania")
        assert "DZ" == country_lookup("Algeria")
        assert "AS" == country_lookup("American Samoa")
        assert "AD" == country_lookup("Andorra")
        assert "AO" == country_lookup("Angola")
        assert "AI" == country_lookup("Anguilla")
        assert "AQ" == country_lookup("Antarctica")
        assert "AG" == country_lookup("Antigua and Barbuda")
        assert "AR" == country_lookup("Argentina")
        assert "AM" == country_lookup("Armenia")
        assert "AW" == country_lookup("Aruba")
        assert "AU" == country_lookup("Australia")
        assert "AT" == country_lookup("Austria")
        assert "AZ" == country_lookup("Azerbaijan")
        assert "BS" == country_lookup("Bahamas")
        assert "BH" == country_lookup("Bahrain")
        assert "BD" == country_lookup("Bangladesh")
        assert "BB" == country_lookup("Barbados")
        assert "BY" == country_lookup("Belarus")
        assert "BE" == country_lookup("Belgium")
        assert "BZ" == country_lookup("Belize")
        assert "BJ" == country_lookup("Benin")
        assert "BM" == country_lookup("Bermuda")
        assert "BT" == country_lookup("Bhutan")
        assert "BO" == country_lookup("Bolivia")
        assert "BQ" == country_lookup("Bonaire, Saint Eustatius and Saba")
        assert "BA" == country_lookup("Bosnia and Herzegovina")
        assert "BW" == country_lookup("Botswana")
        assert "BV" == country_lookup("Bouvet Island")
        assert "BR" == country_lookup("Brazil")
        assert "B1" == country_lookup("British Antarctic Territories")
        assert "IO" == country_lookup("British Indian Ocean Territory")
        assert "VG" == country_lookup("British Virgin Islands")
        assert "BN" == country_lookup("Brunei Darussalam")
        assert "BG" == country_lookup("Bulgaria")
        assert "BF" == country_lookup("Burkina Faso")
        assert "BI" == country_lookup("Burundi")
        assert "CV" == country_lookup("Cabo Verde")
        assert "KH" == country_lookup("Cambodia")
        assert "CM" == country_lookup("Cameroon")
        assert "CA" == country_lookup("Canada")
        assert "KY" == country_lookup("Cayman Islands")
        assert "CF" == country_lookup("Central African Republic")
        assert "TD" == country_lookup("Chad")
        assert "CL" == country_lookup("Chile")
        assert "CN" == country_lookup("China")
        assert "CX" == country_lookup("Christmas Island")
        assert "CC" == country_lookup("Cocos (Keeling) Islands")
        assert "CO" == country_lookup("Colombia")
        assert "KM" == country_lookup("Comoros")
        assert "CG" == country_lookup("Congo Republic")
        assert "CK" == country_lookup("Cook Islands")
        assert "CR" == country_lookup("Costa Rica")
        assert "CI" == country_lookup("Cote d'Ivoire")
        assert "HR" == country_lookup("Croatia")
        assert "CU" == country_lookup("Cuba")
        assert "CW" == country_lookup("Curacao")
        assert "CY" == country_lookup("Cyprus")
        assert "CZ" == country_lookup("Czech Republic")
        assert "DK" == country_lookup("Denmark")
        assert "DJ" == country_lookup("Djibouti")
        assert "DM" == country_lookup("Dominica")
        assert "DO" == country_lookup("Dominican Republic")
        assert "CD" == country_lookup("DR Congo")
        assert "EC" == country_lookup("Ecuador")
        assert "EG" == country_lookup("Egypt")
        assert "SV" == country_lookup("El Salvador")
        assert "GQ" == country_lookup("Equatorial Guinea")
        assert "ER" == country_lookup("Eritrea")
        assert "EE" == country_lookup("Estonia")
        assert "SZ" == country_lookup("Eswatini")
        assert "ET" == country_lookup("Ethiopia")
        assert "FO" == country_lookup("Faeroe Islands")
        assert "FK" == country_lookup("Falkland Islands")
        assert "FJ" == country_lookup("Fiji")
        assert "FI" == country_lookup("Finland")
        assert "FR" == country_lookup("France")
        assert "GF" == country_lookup("French Guiana")
        assert "PF" == country_lookup("French Polynesia")
        assert "TF" == country_lookup("French Southern Territories")
        assert "GA" == country_lookup("Gabon")
        assert "GM" == country_lookup("Gambia")
        assert "GE" == country_lookup("Georgia")
        assert "DE" == country_lookup("Germany")
        assert "GH" == country_lookup("Ghana")
        assert "GI" == country_lookup("Gibraltar")
        assert "GR" == country_lookup("Greece")
        assert "GL" == country_lookup("Greenland")
        assert "GD" == country_lookup("Grenada")
        assert "GP" == country_lookup("Guadeloupe")
        assert "GU" == country_lookup("Guam")
        assert "GT" == country_lookup("Guatemala")
        assert "GG" == country_lookup("Guernsey")
        assert "GN" == country_lookup("Guinea")
        assert "GW" == country_lookup("Guinea-Bissau")
        assert "GY" == country_lookup("Guyana")
        assert "HT" == country_lookup("Haiti")
        assert "HM" == country_lookup("Heard and McDonald Islands")
        assert "HN" == country_lookup("Honduras")
        assert "HK" == country_lookup("Hong Kong")
        assert "HU" == country_lookup("Hungary")
        assert "IS" == country_lookup("Iceland")
        assert "IN" == country_lookup("India")
        assert "ID" == country_lookup("Indonesia")
        assert "IR" == country_lookup("Iran")
        assert "IQ" == country_lookup("Iraq")
        assert "IE" == country_lookup("Ireland")
        assert "IM" == country_lookup("Isle of Man")
        assert "IL" == country_lookup("Israel")
        assert "IT" == country_lookup("Italy")
        assert "JM" == country_lookup("Jamaica")
        assert "JP" == country_lookup("Japan")
        assert "JE" == country_lookup("Jersey")
        assert "JO" == country_lookup("Jordan")
        assert "KZ" == country_lookup("Kazakhstan")
        assert "KE" == country_lookup("Kenya")
        assert "KI" == country_lookup("Kiribati")
        assert "XK" == country_lookup("Kosovo")
        assert "KW" == country_lookup("Kuwait")
        assert "KG" == country_lookup("Kyrgyz Republic")
        assert "LA" == country_lookup("Laos")
        assert "LV" == country_lookup("Latvia")
        assert "LB" == country_lookup("Lebanon")
        assert "LS" == country_lookup("Lesotho")
        assert "LR" == country_lookup("Liberia")
        assert "LY" == country_lookup("Libya")
        assert "LI" == country_lookup("Liechtenstein")
        assert "LT" == country_lookup("Lithuania")
        assert "LU" == country_lookup("Luxembourg")
        assert "MO" == country_lookup("Macau")
        assert "MK" == country_lookup("North Macedonia")
        assert "MG" == country_lookup("Madagascar")
        assert "MW" == country_lookup("Malawi")
        assert "MY" == country_lookup("Malaysia")
        assert "MV" == country_lookup("Maldives")
        assert "ML" == country_lookup("Mali")
        assert "MT" == country_lookup("Malta")
        assert "MH" == country_lookup("Marshall Islands")
        assert "MQ" == country_lookup("Martinique")
        assert "MR" == country_lookup("Mauritania")
        assert "MU" == country_lookup("Mauritius")
        assert "YT" == country_lookup("Mayotte")
        assert "MX" == country_lookup("Mexico")
        assert "FM" == country_lookup("Micronesia, Fed. Sts.")
        assert "MD" == country_lookup("Moldova")
        assert "MC" == country_lookup("Monaco")
        assert "MN" == country_lookup("Mongolia")
        assert "ME" == country_lookup("Montenegro")
        assert "MS" == country_lookup("Montserrat")
        assert "MA" == country_lookup("Morocco")
        assert "MZ" == country_lookup("Mozambique")
        assert "MM" == country_lookup("Myanmar")
        assert "NA" == country_lookup("Namibia")
        assert "NR" == country_lookup("Nauru")
        assert "NP" == country_lookup("Nepal")
        assert "NL" == country_lookup("Netherlands")
        assert "AN" == country_lookup("Netherlands Antilles")
        assert "NC" == country_lookup("New Caledonia")
        assert "NZ" == country_lookup("New Zealand")
        assert "NI" == country_lookup("Nicaragua")
        assert "NE" == country_lookup("Niger")
        assert "NG" == country_lookup("Nigeria")
        assert "NU" == country_lookup("Niue")
        assert "NF" == country_lookup("Norfolk Island")
        assert "KP" == country_lookup("North Korea")
        assert "MP" == country_lookup("Northern Mariana Islands")
        assert "NO" == country_lookup("Norway")
        assert "OM" == country_lookup("Oman")
        assert "PK" == country_lookup("Pakistan")
        assert "PW" == country_lookup("Palau")
        assert "PS" == country_lookup("Palestine")
        assert "PA" == country_lookup("Panama")
        assert "PG" == country_lookup("Papua New Guinea")
        assert "PY" == country_lookup("Paraguay")
        assert "PE" == country_lookup("Peru")
        assert "PH" == country_lookup("Philippines")
        assert "PN" == country_lookup("Pitcairn")
        assert "PL" == country_lookup("Poland")
        assert "PT" == country_lookup("Portugal")
        assert "PR" == country_lookup("Puerto Rico")
        assert "QA" == country_lookup("Qatar")
        assert "RE" == country_lookup("Reunion")
        assert "RO" == country_lookup("Romania")
        assert "RU" == country_lookup("Russia")
        assert "RW" == country_lookup("Rwanda")
        assert "MF" == country_lookup("Saint-Martin")
        assert "WS" == country_lookup("Samoa")
        assert "SM" == country_lookup("San Marino")
        assert "ST" == country_lookup("Sao Tome and Principe")
        assert "SA" == country_lookup("Saudi Arabia")
        assert "SN" == country_lookup("Senegal")
        assert "RS" == country_lookup("Serbia")
        assert "SC" == country_lookup("Seychelles")
        assert "SL" == country_lookup("Sierra Leone")
        assert "SG" == country_lookup("Singapore")
        assert "SX" == country_lookup("Sint Maarten")
        assert "SK" == country_lookup("Slovakia")
        assert "SI" == country_lookup("Slovenia")
        assert "SB" == country_lookup("Solomon Islands")
        assert "SO" == country_lookup("Somalia")
        assert "ZA" == country_lookup("South Africa")
        assert "GS" == country_lookup("South Georgia and South Sandwich Is.")
        assert "KR" == country_lookup("South Korea")
        assert "SS" == country_lookup("South Sudan")
        assert "ES" == country_lookup("Spain")
        assert "LK" == country_lookup("Sri Lanka")
        assert "BL" == country_lookup("St. Barths")
        assert "SH" == country_lookup("St. Helena")
        assert "KN" == country_lookup("St. Kitts and Nevis")
        assert "LC" == country_lookup("St. Lucia")
        assert "PM" == country_lookup("St. Pierre and Miquelon")
        assert "VC" == country_lookup("St. Vincent and the Grenadines")
        assert "SD" == country_lookup("Sudan")
        assert "SR" == country_lookup("Suriname")
        assert "SJ" == country_lookup("Svalbard and Jan Mayen Islands")
        assert "SE" == country_lookup("Sweden")
        assert "CH" == country_lookup("Switzerland")
        assert "SY" == country_lookup("Syria")
        assert "TW" == country_lookup("Taiwan")
        assert "TJ" == country_lookup("Tajikistan")
        assert "TZ" == country_lookup("Tanzania")
        assert "TH" == country_lookup("Thailand")
        assert "TL" == country_lookup("Timor-Leste")
        assert "TG" == country_lookup("Togo")
        assert "TK" == country_lookup("Tokelau")
        assert "TO" == country_lookup("Tonga")
        assert "TT" == country_lookup("Trinidad and Tobago")
        assert "TN" == country_lookup("Tunisia")
        assert "TR" == country_lookup("Türkiye")
        assert "TM" == country_lookup("Turkmenistan")
        assert "TC" == country_lookup("Turks and Caicos Islands")
        assert "TV" == country_lookup("Tuvalu")
        assert "UG" == country_lookup("Uganda")
        assert "UA" == country_lookup("Ukraine")
        assert "AE" == country_lookup("United Arab Emirates")
        assert "US" == country_lookup("United States")
        assert "UM" == country_lookup("United States Minor Outlying Islands")
        assert "VI" == country_lookup("United States Virgin Islands")
        assert "UY" == country_lookup("Uruguay")
        assert "UZ" == country_lookup("Uzbekistan")
        assert "VU" == country_lookup("Vanuatu")
        assert "VA" == country_lookup("Vatican")
        assert "VE" == country_lookup("Venezuela")
        assert "VN" == country_lookup("Vietnam")
        assert "WF" == country_lookup("Wallis and Futuna Islands")
        assert "EH" == country_lookup("Western Sahara")
        assert "YE" == country_lookup("Yemen")
        assert "ZM" == country_lookup("Zambia")
        assert "ZW" == country_lookup("Zimbabwe")