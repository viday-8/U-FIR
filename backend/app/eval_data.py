"""Held-out evaluation set for the rule-based extractor. Written AFTER the rules, in styles the seed cases do not use
(honorifics, 'Age: 40 yrs', 'Vill.', Telangana plates, Section ... of the NDPS Act, 1985, decimals, 'cans').
Gold labels are hand-written by the developer, not adjudicated by two annotators. Synthetic text, fictional people."""

EVAL_DOCS = [
    {"id": "E1 hybrid-honorifics", "text": """Sri Venkata Subbaiah, S/o Late Narasimham, Age: 40 yrs, R/o Vill. Gollapalem, was found near Gollapalem cross roads on 05-03-2026 with 24 Tetra packs of IML in scooter AP 16 EK 3342. Case booked u/s 34(a) of A.P. Excise Act.""",
     "gold": [("person", "Venkata Subbaiah"), ("place", "Gollapalem"), ("date", "05-03-2026"), ("quantity", "24 Tetra packs"), ("item", "IML"), ("vehicle", "AP 16 EK 3342"), ("legal_section", "u/s 34(a) of A.P. Excise Act")]},
    {"id": "E2 women-arrack", "text": """Smt. Padmavathi, W/o Sri Ramana Murthy, aged 38 years, resident of Pedana, was found selling 12 bottles of arrack on 11.04.2026. The case is registered under Section 7A of the AP Prohibition Act.""",
     "gold": [("person", "Padmavathi"), ("place", "Pedana"), ("quantity", "12 bottles"), ("item", "arrack"), ("date", "11.04.2026"), ("legal_section", "Section 7A of the AP Prohibition Act")]},
    {"id": "E3 panchas-and-cans", "text": """Recovered 2 cans of 35 litres each containing ID liquor from scooter TS 09 FA 1234 near Kothapet. Accused Kotha Srinivas, S/o Kotha Ramulu, R/o Kothapet, was apprehended in the presence of panchas Sri B. Ramu and Sri K. Venkateswarlu.""",
     "gold": [("quantity", "2 cans"), ("quantity", "35 litres"), ("item", "ID liquor"), ("vehicle", "TS 09 FA 1234"), ("place", "Kothapet"), ("person", "Kotha Srinivas"), ("person", "B. Ramu"), ("person", "K. Venkateswarlu")]},
    {"id": "E4 decoy", "text": """On 02-06-2026 at 18:15 hrs the decoy witness purchased one quarter bottle of NDPL from Ch. Rajamma, W/o Ch. Appanna, aged 55, of Gannavaram Village. The seller's stock of 18 bottles was seized.""",
     "gold": [("date", "02-06-2026"), ("item", "NDPL"), ("person", "Ch. Rajamma"), ("place", "Gannavaram Village"), ("quantity", "18 bottles")]},
    {"id": "E5 ganja-decimal", "text": """Seized 12.5 kgs of dry ganja from a black bag carried by Anil Kumar, S/o Ravi Kumar, 26 years, R/o Chintapalli, travelling by bus APSRTC AP 31 Z 4455 on 19/08/2026. Booked under Sec. 20(b)(ii)(A) of the NDPS Act, 1985.""",
     "gold": [("quantity", "12.5 kgs"), ("item", "dry ganja"), ("person", "Anil Kumar"), ("place", "Chintapalli"), ("vehicle", "AP 31 Z 4455"), ("date", "19/08/2026"), ("legal_section", "Sec. 20(b)(ii)(A) of the NDPS Act, 1985")]},
    {"id": "E6 remand", "text": """Accused Venkata Subbaiah and Kotha Srinivas were produced before the Judicial Magistrate of First Class, Gollapalem on 06-03-2026 and remanded to judicial custody for 14 days.""",
     "gold": [("person", "Venkata Subbaiah"), ("person", "Kotha Srinivas"), ("place", "Gollapalem"), ("date", "06-03-2026")]},
]
