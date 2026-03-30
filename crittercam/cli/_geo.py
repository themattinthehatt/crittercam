"""Geographic validation constants and prompts for SpeciesNet geofencing."""

import re

# ISO 3166-1 alpha-3 codes accepted by SpeciesNet for geofencing.
VALID_COUNTRY_CODES = frozenset({
    'ABW', 'AFG', 'AGO', 'AIA', 'ALA', 'ALB', 'AND', 'ARE', 'ARG', 'ARM',
    'ASM', 'ATA', 'ATF', 'ATG', 'AUS', 'AUT', 'AZE', 'BDI', 'BEL', 'BEN',
    'BES', 'BFA', 'BGD', 'BGR', 'BHR', 'BHS', 'BIH', 'BLM', 'BLR', 'BLZ',
    'BMU', 'BOL', 'BRA', 'BRB', 'BRN', 'BTN', 'BVT', 'BWA', 'CAF', 'CAN',
    'CCK', 'CHE', 'CHL', 'CHN', 'CIV', 'CMR', 'COD', 'COG', 'COK', 'COL',
    'COM', 'CPV', 'CRI', 'CUB', 'CUW', 'CXR', 'CYM', 'CYP', 'CZE', 'DEU',
    'DJI', 'DMA', 'DNK', 'DOM', 'DZA', 'ECU', 'EGY', 'ERI', 'ESH', 'ESP',
    'EST', 'ETH', 'FIN', 'FJI', 'FLK', 'FRA', 'FRO', 'FSM', 'GAB', 'GBR',
    'GEO', 'GGY', 'GHA', 'GIB', 'GIN', 'GLP', 'GMB', 'GNB', 'GNQ', 'GRC',
    'GRD', 'GRL', 'GTM', 'GUF', 'GUM', 'GUY', 'HKG', 'HMD', 'HND', 'HRV',
    'HTI', 'HUN', 'IDN', 'IMN', 'IND', 'IOT', 'IRL', 'IRN', 'IRQ', 'ISL',
    'ISR', 'ITA', 'JAM', 'JEY', 'JOR', 'JPN', 'KAZ', 'KEN', 'KGZ', 'KHM',
    'KIR', 'KNA', 'KOR', 'KWT', 'LAO', 'LBN', 'LBR', 'LBY', 'LCA', 'LIE',
    'LKA', 'LSO', 'LTU', 'LUX', 'LVA', 'MAC', 'MAF', 'MAR', 'MCO', 'MDA',
    'MDG', 'MDV', 'MEX', 'MHL', 'MKD', 'MLI', 'MLT', 'MMR', 'MNE', 'MNG',
    'MNP', 'MOZ', 'MRT', 'MSR', 'MTQ', 'MUS', 'MWI', 'MYS', 'MYT', 'NAM',
    'NCL', 'NER', 'NFK', 'NGA', 'NIC', 'NIU', 'NLD', 'NOR', 'NPL', 'NRU',
    'NZL', 'OMN', 'PAK', 'PAN', 'PCN', 'PER', 'PHL', 'PLW', 'PNG', 'POL',
    'PRI', 'PRK', 'PRT', 'PRY', 'PSE', 'PYF', 'QAT', 'REU', 'ROU', 'RUS',
    'RWA', 'SAU', 'SDN', 'SEN', 'SGP', 'SGS', 'SHN', 'SJM', 'SLB', 'SLE',
    'SLV', 'SMR', 'SOM', 'SPM', 'SRB', 'SSD', 'STP', 'SUR', 'SVK', 'SVN',
    'SWE', 'SWZ', 'SXM', 'SYC', 'SYR', 'TCA', 'TCD', 'TGO', 'THA', 'TJK',
    'TKL', 'TKM', 'TLS', 'TON', 'TTO', 'TUN', 'TUR', 'TUV', 'TWN', 'TZA',
    'UGA', 'UKR', 'UMI', 'URY', 'USA', 'UZB', 'VAT', 'VCT', 'VEN', 'VGB',
    'VIR', 'VNM', 'VUT', 'WLF', 'WSM', 'YEM', 'ZAF', 'ZMB', 'ZWE',
})

# admin1_region: state/province abbreviation, e.g. 'CT', 'CA', 'ON'
ADMIN1_RE = re.compile(r'^[A-Z0-9]{1,8}$')


def prompt_country() -> str | None:
    """Prompt for an ISO 3166-1 alpha-3 country code with validation.

    Returns:
        validated country code, or None if the user skips
    """
    while True:
        raw = input(
            'Enter country code for SpeciesNet geofencing (ISO 3166-1 alpha-3, e.g. USA) '
            '[leave blank to skip]: '
        ).strip().upper()
        if not raw:
            return None
        if raw in VALID_COUNTRY_CODES:
            return raw
        print(f'  {raw!r} is not a recognised ISO 3166-1 alpha-3 code. Try again.')


def prompt_admin1_region() -> str | None:
    """Prompt for a state/province abbreviation with format validation.

    Returns:
        validated admin1 region code, or None if the user skips
    """
    while True:
        raw = input(
            'Enter state/province abbreviation (e.g. CT for Connecticut) '
            '[leave blank to skip]: '
        ).strip().upper()
        if not raw:
            return None
        if ADMIN1_RE.match(raw):
            return raw
        print(f'  {raw!r} is not a valid abbreviation. Use 1–8 uppercase letters/digits.')
