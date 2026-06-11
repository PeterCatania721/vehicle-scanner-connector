# KESI Preventivo bolli matrix rows (field index -> Italian label).
# Row 11 has no standard matrix fields on production KESI; Cofano uses index 12.

BOLLI_PANEL_ROWS = [
    (1, 'Parafango Ant Sx'),
    (2, 'Porta Ant SX'),
    (3, 'Porta Post SX'),
    (4, 'Paraf Post Sx'),
    (5, 'Montante Sx'),
    (6, 'Parafango Ant Dx'),
    (7, 'Porta Ant Dx'),
    (8, 'Porta Post Dx'),
    (9, 'Parafango Post Dx'),
    (10, 'Montante DX'),
    (12, 'Cofano ANT'),
    (13, 'Tetto'),
    (14, 'Portellone/Baule'),
    (15, 'Baule Sotto'),
    (16, 'Sottoporta sx'),
    (17, 'Sottoporta dx'),
    (18, 'Torpedo'),
]

BOLLI_LEFT_ROWS = [row for row in BOLLI_PANEL_ROWS if row[0] <= 5]
BOLLI_RIGHT_ROWS = [row for row in BOLLI_PANEL_ROWS if row[0] > 5]

BOLLI_FIELD_INDEXES = [index for index, _label in BOLLI_PANEL_ROWS]