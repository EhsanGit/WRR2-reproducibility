"""
extract_urls.py  (download, step 1)

Collects the URLs of all NetCDF files that the partners published for each model,
experiment and catchment (OPeNDAP/THREDDS catalogues, Zenodo records, web folders,
the mHM S3 bucket) and writes them to <model>_<experiment>.txt lists for wget.

base_url below lists the partner sources. Entries that are commented out were
downloaded in earlier rounds; uncomment the ones to fetch again.

Inputs:  base_url (in this file)
Outputs: <model>_<experiment>.txt in the current folder

Usage:
    python extract_urls.py
Needs requests, beautifulsoup4, selenium and webdriver-manager, and a Chromium
binary (CHROME_BINARY) for pages that need a browser.

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""
import re
import subprocess
import requests
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CHROME_BINARY = "/usr/bin/chromium-browser"


def get_installed_chrome_version(binary_path=CHROME_BINARY):
    """Return the installed Chrome/Chromium version string (e.g. '150.0.7871.114'), or None if it can't be determined."""
    try:
        output = subprocess.check_output([binary_path, "--version"], text=True)
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output)
        return match.group(1) if match else None
    except Exception as e:
        logging.error(f"Could not determine installed Chrome version: {e}")
        return None

# Dictionary of base URLs
base_url = {
    "CLM": {
        "Exp10": {
            # "Europe": ["https://datapub.fz-juelich.de/slts/4DHydro/data_clm35_europe_3km_remap_EMO-pr-forcing/"],
            # "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp10_clm35/"],
            "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp10_clm35_5km/"],
            # "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp10_clm35/"],
            # "Tugela": None
        },
    #     "Exp20": {
    #         "Po": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp2_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp2_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp21": {
    #         "Po": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp21_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp21_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp30": {
    #         "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp30_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp30_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp31": {
    #         "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp31_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp31_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp32": {
    #         "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp32_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp32_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp33": {
    #         "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp33_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp33_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp34": {
    #         "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp34_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp34_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp41": {
    #         "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp41_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp41_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp42": {
    #         "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp42_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp42_clm35/"],
    #         "Tugela": None
    #     },
    #     "Exp44": {
    #         "Po":    ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp44_clm35/"],
    #         "Rhine": ["https://datapub.fz-juelich.de/slts/4DHydro/data_WP5_Exp44_clm35/"],
    #         "Tugela": None
        }
    # },
    # "GEOframe": {
    #     "Exp10": ["https://zenodo.org/records/10776668"],
    #     "Exp20": ["https://zenodo.org/records/13292319"],
    #     "Exp21": ["https://zenodo.org/records/13361498"]
    # },
    # "JULES": {
        # "Exp10": ["https://gws-access.jasmin.ac.uk/public/4dhydro/"],
        # "Exp20": None,
        # "Exp21": ["https://gws-access.jasmin.ac.uk/public/4dhydro/"],
        # "Exp30": ["https://gws-access.jasmin.ac.uk/public/4dhydro/"],
        # "Exp31": ["https://gws-access.jasmin.ac.uk/public/4dhydro/"],
        # "Exp32": ["https://gws-access.jasmin.ac.uk/public/4dhydro/"],
        # "Exp34": ["https://gws-access.jasmin.ac.uk/public/4dhydro/"],
    # },
    # "mHM": {
    #     "Exp10": ["https://www.ufz.de/record/dmp/archive/15044/en/"],
    #     "Exp20": ["https://www.ufz.de/record/dmp/archive/15172/en/"],
    #     "Exp21": ["https://www.ufz.de/record/dmp/archive/15173/en/"]
    # },
    # "PCRGLOBWB": {
    #     "Exp10": {
    #         "Po": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp10/pcrglobwb_emo_po_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp10/pcrglobwb_emo_po_30sec/"]
    #         },
    #         "Rhine": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp10/pcrglobwb_emo_rhine_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp10/pcrglobwb_emo_rhine_30sec/"]
    #         },
    #         "Tugela": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp10/pcrglobwb_chirps_tugela_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp10/pcrglobwb_chirps_tugela_30sec/"]
    #         },
    #     },
    #     "Exp20": {
    #         "Po": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp20/pcrglobwb_emo_po_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp20/pcrglobwb_emo_po_30sec/"]
    #         },
    #         "Rhine": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp20/pcrglobwb_emo_rhine_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp20/pcrglobwb_emo_rhine_30sec/"]
    #         },
    #         "Tugela": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp20/pcrglobwb_chirps_tugela_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/exp20/pcrglobwb_chirps_tugela_30sec/"]
    #         },
    #     },
    #     "Exp30": {
    #         "Po": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp30/pcrglobwb_mergedera5gpmsm2a_po_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp30/pcrglobwb_mergedera5gpmsm2a_po_30sec/"]
    #         },
    #         "Rhine": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp30/pcrglobwb_mergedera5gpmsm2a_rhine_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp30/pcrglobwb_mergedera5gpmsm2a_rhine_30sec/"]
    #         },
    #         "Tugela": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp30/pcrglobwb_mergedera5gpmsm2a_tugela_03min/"],              
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp30/pcrglobwb_mergedera5gpmsm2a_tugela_30sec/"]
    #         },
    #     },
    #     "Exp31": {
    #         "Po": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp31/pcrglobwb_mergedera5gpmsm2a_po_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp31/pcrglobwb_mergedera5gpmsm2a_po_30sec/"]
    #             },
    #         "Rhine": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp31/pcrglobwb_mergedera5gpmsm2a_rhine_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp31/pcrglobwb_mergedera5gpmsm2a_rhine_30sec/"]
    #         },
    #         "Tugela": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp31/pcrglobwb_mergedera5gpmsm2a_tugela_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp31/pcrglobwb_mergedera5gpmsm2a_tugela_30sec/"]
    #         },
    #     },
    #     "Exp32": {
    #         "Po": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp32/pcrglobwb_mergedera5gpmsm2a_po_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp32/pcrglobwb_mergedera5gpmsm2a_po_30sec/"]
    #         },
    #         "Rhine": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp32/pcrglobwb_mergedera5gpmsm2a_rhine_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp32/pcrglobwb_mergedera5gpmsm2a_rhine_30sec/"]
    #         },
    #         "Tugela": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp32/pcrglobwb_mergedera5gpmsm2a_tugela_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1739790742%5D/original/exp32/pcrglobwb_mergedera5gpmsm2a_tugela_30sec/"]
    #         },
    #     },
    #     "Exp34": {
    #         "Po": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1747040542%5D/original/exp34/pcrglobwb_mergedera5gpmsm2a_po_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1747040542%5D/original/exp34/pcrglobwb_mergedera5gpmsm2a_po_30sec/"]
    #         },
    #         "Rhine": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1747040542%5D/original/exp34/pcrglobwb_mergedera5gpmsm2a_rhine_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1747040542%5D/original/exp34/pcrglobwb_mergedera5gpmsm2a_rhine_30sec/"]
    #         },
    #         "Tugela": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1747040542%5D/original/exp34/pcrglobwb_mergedera5gpmsm2a_tugela_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1747040542%5D/original/exp34/pcrglobwb_mergedera5gpmsm2a_tugela_30sec/"]
    #         },
    #     },
    #     "delineation": {
    #         "Po": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/pcrglobwb_emo_po_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/pcrglobwb_emo_po_30sec/"]
    #         },
    #         "Rhine": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/pcrglobwb_emo_rhine_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/pcrglobwb_emo_rhine_30sec/"]
    #         },
    #         "Tugela": {
    #             "03min": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/pcrglobwb_chirps_tugela_03min/"],
    #             "30sec": ["https://geo.public.data.uu.nl/vault-4dhydro/data%5B1726121821%5D/original/pcrglobwb_chirps_tugela_30sec/"]
    #         },
    #     },
    # },
    # "TETIS": {
    #     "Exp10": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/10885651"],
    #             "30sec": ["https://zenodo.org/records/10891435"],
    #             "15sec": ["https://zenodo.org/records/10958535"],
    #             "7p5sec": ["https://zenodo.org/records/10974783"]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/11518476"],
    #             "30sec": ["https://zenodo.org/records/11518681"],
    #             "15sec": ["https://zenodo.org/records/11518687"],
    #             "7p5sec": ["https://zenodo.org/records/11518723"]
    #         },
    #     },
    #     "Exp20": {
    #         "Po": ["https://zenodo.org/records/12732494"],
    #         "Tugela": ["https://zenodo.org/records/14179240"]
    #     },
    #     "Exp21": {
    #         "Po": {
    #             "30sec": ["https://zenodo.org/records/12732502"],
    #             "15sec": ["https://zenodo.org/records/13151472"],
    #             "7p5sec": [
    #                 "https://zenodo.org/records/13236591",  # Part1
    #                 "https://zenodo.org/records/13253466",  # Part2
    #                 "https://zenodo.org/records/13268498",  # Part3
    #                 "https://zenodo.org/records/13268520"   # Part4
    #             ]
    #         },
    #         "Tugela": {
    #             "30sec": ["https://zenodo.org/records/14179271"],
    #             "15sec":  ["https://zenodo.org/records/14186550"],
    #             "7p5sec": ["https://zenodo.org/records/14186601"]
    #         }
    #     },
    #     "Exp30": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/14499899"],
    #             "30sec": ["https://zenodo.org/records/14500498"],
    #             "15sec": ["https://zenodo.org/records/14500689"],
    #             "7p5sec": [
    #                 "https://zenodo.org/records/14500766",  # Part1
    #                 "https://zenodo.org/records/14500907"   # Part2
    #             ]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/14501270"],
    #             "30sec": ["https://zenodo.org/records/14501307"],
    #             "15sec": ["https://zenodo.org/records/14501326"],
    #             "7p5sec": ["https://zenodo.org/records/14501355"]
    #             }
    #     },
    #     "Exp31": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/14921597"],
    #             "30sec": ["https://zenodo.org/records/14921680"],
    #             "15sec": ["https://zenodo.org/uploads/14921710"],
    #             "7p5sec": [
    #                 "https://zenodo.org/uploads/14921732",  # Part1,
    #                 "https://zenodo.org/uploads/14922046"   # Part2
    #                 ]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/14863312"],
    #             "30sec": ["https://zenodo.org/records/14863331"],
    #             "15sec": ["https://zenodo.org/records/14863340"],
    #             "7p5sec": ["https://zenodo.org/records/14863357"]
    #         }
    #     },
    #     "Exp32": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/14843568"],
    #             "30sec": ["https://zenodo.org/records/14843884"],
    #             "15sec": ["https://zenodo.org/records/14843897"],
    #             "7p5sec": [
    #                 "https://zenodo.org/records/14843937",  # Part1
    #                 "https://zenodo.org/records/14843995"   # Part2
    #                 ]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/14843129"],
    #             "30sec": ["https://zenodo.org/records/14843438"],
    #             "15sec": ["https://zenodo.org/records/14843465"],
    #             "7p5sec": ["https://zenodo.org/records/14843482"]
    #         }
    #     },
    #     "Exp34": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/14973768"],
    #             "30sec": ["https://zenodo.org/records/14973834"],
    #             "15sec": ["https://zenodo.org/records/14973864"],
    #             "7p5sec": [
    #                 "https://zenodo.org/records/14974010",  # Part1
    #                 "https://zenodo.org/records/14974153"   # Part2
    #                 ]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/14938677"],
    #             "30sec": ["https://zenodo.org/records/14938649"],
    #             "15sec": ["https://zenodo.org/records/14938709"],
    #             "7p5sec": ["https://zenodo.org/records/14938738"]
    #         }
    #     },
    #     "Exp40": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/14499899"],
    #             "30sec": ["https://zenodo.org/records/14500498"],
    #             "15sec": ["https://zenodo.org/records/14500689"],
    #             "7p5sec": [
    #                 "https://zenodo.org/records/14500766",  # Part1
    #                 "https://zenodo.org/records/14500907"   # Part2
    #             ]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/14501270"],
    #             "30sec": ["https://zenodo.org/records/14501307"],
    #             "15sec": ["https://zenodo.org/records/14501326"],
    #             "7p5sec": ["https://zenodo.org/records/14501355"]
    #         }
    #     },
    #     "Exp41": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/15102162"],
    #             "30sec": ["https://zenodo.org/records/15102181"],
    #             "15sec": ["https://zenodo.org/records/15102203"],
    #             "7p5sec": [
    #                 "https://zenodo.org/records/15102261",  # Part1
    #                 "https://zenodo.org/records/15102343"   # Part2
    #                 ]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/15189901"],
    #             "30sec": ["https://zenodo.org/records/15189947"],
    #             "15sec": ["https://zenodo.org/records/15189966"],
    #             "7p5sec": ["https://zenodo.org/records/15190000"]
    #         }
    #     },
    #     "Exp42": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/15124245"],
    #             "30sec": ["https://zenodo.org/records/15124267"],
    #             "15sec": ["https://zenodo.org/records/15124300"],
    #             "7p5sec": [
    #                 "https://zenodo.org/records/15124957",  # Part1
    #                 "https://zenodo.org/records/15125073"   # Part2
    #                 ]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/15203660"],
    #             "30sec": ["https://zenodo.org/records/15203710"],
    #             "15sec": ["https://zenodo.org/records/15203757"],
    #             "7p5sec": ["https://zenodo.org/records/15203794"]
    #         }
    #     },
    #     "Exp44": {
    #         "Po": {
    #             "0p0667deg": ["https://zenodo.org/records/15188899"],
    #             "30sec": ["https://zenodo.org/records/15188933"],
    #             "15sec": ["https://zenodo.org/records/15188987"],
    #             "7p5sec": [
    #                 "https://zenodo.org/records/15189122",  # Part1
    #                 "https://zenodo.org/records/15189690"   # Part2
    #                 ]
    #         },
    #         "Tugela": {
    #             "0p0667deg": ["https://zenodo.org/records/15207507"],
    #             "30sec": ["https://zenodo.org/records/15207538"],
    #             "15sec": ["https://zenodo.org/records/15207567"],
    #             "7p5sec": ["https://zenodo.org/records/15207599"]
    #         }
    #     },
    # },
    # "wflow_sbm": {
    #     "Exp10": {
    #         "Po": ["https://opendap.4tu.nl/thredds/catalog/data2/djht/1abe4de8-ecef-48c0-bbde-c599357c4102/1/catalog.html"],
    #         "Rhine": ["https://opendap.4tu.nl/thredds/catalog/data2/djht/c4e053ad-0d80-43d2-9d10-e61a55b91246/1/catalog.html"],
    #         "Tugela": ["https://opendap.4tu.nl/thredds/catalog/data2/djht/7305a608-bb1e-4318-8f86-24a3582361ad/1/catalog.html"]
    #     },
    #     "Exp20": None,
    #     "Exp21": {
    #         "Po": ["https://opendap.4tu.nl/thredds/catalog/data2/djht/6e14e25b-cb2b-434e-a852-1340ed8f0eda/1/catalog.html"],
    #         "Rhine": ["https://opendap.4tu.nl/thredds/catalog/data2/djht/018b9124-ffbf-45f2-979a-7a22d465564b/1/catalog.html"],
    #         "Tugela": ["https://opendap.4tu.nl/thredds/catalog/data2/djht/59d94d48-21c3-40c5-b120-5d543b865737/1/catalog.html"]
    #     }
    # }
}

#%% Internal functions
def extract_urls_for_all_combinations(base_url, save_to_file=True):
    """
    Function to extract all NetCDF file URLs for all possible combinations
    of model, experiment, and catchment in the base URL dictionary.
    
    Args:
        save_to_file (bool, optional): Whether to save the URLs to .txt files. Defaults to True.
    """
    for model_name, experiments in base_url.items():
        model_has_urls = False  # Track if the model has any valid URLs
        for experiment_name, catchments in experiments.items():
            experiment_has_urls = False  # Track if the experiment has any valid URLs

            if model_name == "mHM":
                # Handle mHM-specific logic
                mhm_urls_logic(save_to_file=save_to_file)
                experiment_has_urls = True
                model_has_urls = True
            elif isinstance(catchments, dict):
                for catchment_name, url in catchments.items():
                    if url is not None:
                        extract_url(base_url, model_name, experiment_name, catchment_name, save_to_file)
                        # print(f"\t Extracted URLs for {model_name} {experiment_name} {catchment_name}")
                        # logging.info(f"\t Extracted URLs for {model_name} {experiment_name} {catchment_name}")
                        experiment_has_urls = True  # Set to True if there's a valid URL
            else:
                if catchments is not None:
                    extract_url(base_url, model_name, experiment_name, save_to_file=save_to_file)
                    experiment_has_urls = True  # Set to True if there's a valid URL

            # Only print if there were valid URLs for this experiment
            if experiment_has_urls:
                # print(f"Extracted URLs for {model_name} {experiment_name}")
                logging.info(f"Extracted URLs for {model_name} {experiment_name}")
                model_has_urls = True  # Set to True if the model has any valid URLs

        # Only print for the model if it has at least one valid URL
        if model_has_urls:
            # print(f"Finished extracting for {model_name}")
            logging.info(f"Finished extracting for {model_name}")

def mhm_urls_logic(start_year: int = 1990, end_year: int = 2022, save_to_file: bool = True):
    """
    Extract URLs for netCDF files for the mHM model.

    Parameters:
    - start_year (int): Start year for the range of netCDF files.
    - end_year (int): End year for the range of netCDF files.
    - save_to_file (bool): Whether to save the URLs to files or not. Default is True.
    """
    base_url = "https://minio.ufz.de/4dhydro/mHM/tier2/"
    experiments = ["exp10", "exp20", "exp21"]
    variables = ["et", "mask", "q", "sm", "tws", "uparea"]
    forcings = ["emo"]
    basins = ["po", "rhine", "tugela"]
    resolutions = {"exp10": ["0p0625deg", "0p015625deg"], 
                   "exp20": ["0p0625deg"], 
                   "exp21": ["0p015625deg"]}

    # Dictionary to hold URLs by experiment
    experiment_urls = {exp: [] for exp in experiments}

    # Generate URLs and organize them by experiment
    for exp in experiments:
        for basin in basins:
            for res in resolutions.get(exp, []):
                for var in variables:
                    for forcing in forcings:

                        # Only one file for mask and uparea
                        if var == "mask" or var == "uparea":
                            file_name = f"mhm_{forcing}_{var}_{basin}_{res}.nc"
                            if exp == "exp10":
                                url = f"{base_url}{file_name}"
                            else:
                                url = f"{base_url}{exp}/{file_name}"
                            experiment_urls[exp].append(url)
                        else:
                            # Loop over years
                            for year in range(start_year, end_year + 1):
                                # Pattern is like: mhm_emo_tws_rhine_0p125deg_daily_20210101_20211231.nc
                                file_pattern = f"mhm_{forcing}_{var}_{basin}_{res}_daily_{exp}_"
                                file_name = f"{file_pattern}{year}0101_{year}1231.nc"
                                if exp == "exp10":
                                    url = f"{base_url}{file_name}"
                                else:
                                    url = f"{base_url}{exp}/{file_name}"
                                experiment_urls[exp].append(url)

    if save_to_file:
        for exp, urls in experiment_urls.items():
            file_name = f"mhm_{exp}.txt"
            with open(file_name, "w") as f:
                for url in urls:
                    f.write(f"{url}\n")
            logging.info(f"URLs for {exp} saved to {file_name}")

    # Flatten all URLs into a single list for return
    all_urls = [url for urls in experiment_urls.values() for url in urls]
    return all_urls

def extract_links(data):
    """
    This function recursively extracts all links from a nested dictionary. to extract links from.

    Returns:
        A list of all links found in the dictionary.
    """
    links = []
    if isinstance(data, dict):
        for value in data.values():
            links.extend(extract_links(value))
    elif isinstance(data, list):
        links.extend([item for item in data if isinstance(item, str)])
    elif isinstance(data, str):
        links.append(data)
    return links

def extract_url(base_url, model_name: str, experiment_name: str, catchment_name='', save_to_file=True):
    """
    Function to extract all NetCDF file URLs from a given model's experiment and catchment.

    Args:
        model_name (str): Name of the model (e.g., "wflowsbm").
        experiment_name (str): Name of the experiment (e.g., "Exp10").
        catchment_name (str, optional): Name of the catchment (e.g., "Po"). Defaults to an empty string.
        save_to_file (bool, optional): Whether to save the URLs to a text file. Defaults to True.

    Returns:
        list: A list of NetCDF URLs.
    """
    data = base_url.get(model_name, {}).get(experiment_name, {})

    if model_name == "GEOframe" or model_name == "JULES":
        url_list = [data]
    elif data is None:
        logging.info(f"No URL found for {model_name} {experiment_name} {catchment_name}")
        return []
    else:
        url_list = [value for value in data.values() if value is not None]

        if model_name == "PCRGLOBWB":
            url_list = [item[key] for item in url_list for key in item.keys()]
            delineation_data = base_url.get("PCRGLOBWB", {}).get("delineation", {})
            delineation_urls = [value for value in delineation_data.values() if value is not None]
            delineation_urls = [item[key] for item in delineation_urls for key in item.keys()]
            url_list.extend(delineation_urls)
            # url_list = list(set(url_list))
            url_list = list(map(list, set(map(tuple, url_list))))
        elif model_name == "TETIS":
            url_list = extract_links(data)

    if url_list is not None:
        URLs = []
        for url in url_list:
            if type(url) == list:
                url = ''.join(url)
            response = requests.get(url)

            if model_name.lower() == "wflow_sbm" and response.status_code == 200:
                model_name = model_name.replace("_", "").lower() # Corrected placement
                soup = BeautifulSoup(response.content, 'html.parser')
                names = [element.text for element in soup.find_all('a', href=True) if element.text.startswith(model_name)]
                base_url_for_wflow = url.rsplit('/', 2)[0] + '/' + url.rsplit('/', 2)[1] + '/' # Use a different variable name to avoid shadowing
                netcdf_names = [name.split("/")[-1] for name in names]
                base_url_for_wflow = base_url_for_wflow.replace("catalog", "fileServer")
                urls = [base_url_for_wflow + name for name in netcdf_names]
                URLs.extend(urls)
            elif response.status_code == 200:
                if url.find("zenodo") != -1:
                    record_id = url.split("/")[-1]
                    api_url = f"https://zenodo.org/api/records/{record_id}"
                    response_zenodo = requests.get(api_url)
                    url_data = response_zenodo.json()
                    for file in url_data['files']:
                        if file['key'].endswith('.nc'):
                            urls = [f"{url}/files/{file['key']}"]
                            URLs.extend(urls)
                else:
                    # Set up headless Chrome
                    chrome_options = Options()
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.binary_location = CHROME_BINARY

                    service = None # Initialize service to None
                    installed_version = get_installed_chrome_version()
                    try:
                        if installed_version:
                            # Match the ChromeDriver version to the actually installed browser version
                            logging.info(f"Attempting to install ChromeDriver matching installed Chrome version {installed_version}")
                            service = ChromeService(ChromeDriverManager(driver_version=installed_version).install())
                        else:
                            raise RuntimeError("Installed Chrome version could not be determined")
                    except Exception as e:
                        logging.error(f"Error installing ChromeDriver for version {installed_version}: {e}")
                        logging.info("Falling back to installing the latest available ChromeDriver.")
                        try:
                            # Fallback to the latest if the specific version fails
                            service = ChromeService(ChromeDriverManager().install())
                        except Exception as e_fallback:
                            logging.error(f"Failed to install any ChromeDriver: {e_fallback}")
                            return [] # Cannot proceed without a driver

                    if service: # Only proceed if a service object was successfully created
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                        try:
                            driver.get(url)
                            driver.implicitly_wait(5)
                            elements = driver.find_elements(By.CSS_SELECTOR, 'a[href$=".nc"]')
                            urls = [element.get_attribute('href') for element in elements]
                            urls = [u.replace("catalog", "fileServer") for u in urls if "/.nc" not in u]
                            URLs.extend(urls)
                        finally:
                            driver.quit()
            else:
                logging.error(f"Failed to retrieve the page. Status code: {response.status_code} for URL: {url}")
                return []

        URLs = list(set(URLs))
        URLs.sort()

        if save_to_file:
            file_name = f"{model_name}_{experiment_name}.txt"
            file_name = file_name.lower()
            file_path = f"{file_name}"
            with open(file_path, "w") as f:
                for url in URLs:
                    f.write(f"{url}\n")

        return URLs
    else:
        logging.info(f"No URL found for {model_name} {experiment_name} {catchment_name}")
        return []

#%% Run the function to extract URLs for all combinations
extract_urls_for_all_combinations(base_url)
