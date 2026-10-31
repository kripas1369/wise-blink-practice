"""The 5 official test targets of the "Planet X and SPHEREx" challenge."""

OFFICIAL_TARGETS = [
    {
        "key": "barnard",
        "label": "Barnard's Star",
        "simbad": "Barnard's Star",
        "kind": "mover",
        "look_for": "The fastest-moving star in the sky (about 10.4 arcsec/yr). Watch it walk.",
    },
    {
        "key": "eps_ind_b",
        "label": "Epsilon Indi B",
        "simbad": "eps Ind B",
        "kind": "mover",
        "look_for": "A pair of brown dwarfs (about 4.7 arcsec/yr). A small shift, about one pixel.",
    },
    {
        "key": "wise0855",
        "label": "WISE 0855",
        "simbad": "WISE J085510.83-071442.5",
        "kind": "cold",
        "look_for": "The coldest known brown dwarf. Invisible at short wavelengths, visible in D5-D6.",
        "challenge_position": "08h55m10.831s -07d14m42.53s",
    },
    {
        "key": "rw_aur",
        "label": "RW Aurigae",
        "simbad": "RW Aur",
        "kind": "variable",
        "look_for": "A young star that dims and brightens.",
    },
    {
        "key": "r_dra",
        "label": "R Draconis",
        "simbad": "R Dra",
        "kind": "variable",
        "look_for": "A pulsating giant (Mira); brightness rises and falls over about 245 days.",
    },
]
