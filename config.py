"""
config.py — Tüm sistem ayarları
"""

# ── TELEGRAM ──────────────────────────────────────────
TELEGRAM_TOKEN   = "8731413161:AAG8TR91BrQ_OTh-tRBcOSx4fkzk0ke6TUk"
TELEGRAM_CHAT_ID = "947636416"

# ── SİMÜLASYON ────────────────────────────────────────
SIM_POZISYON_TL = 10_000

# ── BIST TRADE (Kısa Vade Teknik) ─────────────────────
BIST_TRADE = {
    "ema_hizli":    20,
    "ema_yavas":    50,
    "rsi_periyot":  14,
    "rsi_min":      40,
    "rsi_max":      60,
    "atr_periyot":  14,
    "atr_stop":     2.0,
    "atr_tp1":      2.0,
    "atr_tp2":      3.5,
    "atr_tp3":      5.0,
    "min_puan":     65,
    "tarama_saati": "09:10",
}

# ── BIST TEMEL (Orta-Uzun Vade) ───────────────────────
BIST_TEMEL = {
    "max_fk":         15,
    "max_pddd":       2.5,
    "min_roe":        0.15,
    "min_kar_buyume": 0.10,
    "max_borc_ok":    1.0,
    "min_getiri_pot": 0.25,
    "max_secim":      10,
}

# ── KRİPTO ────────────────────────────────────────────
KRIPTO = {
    "coinler": [
        "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
        "DOGEUSDT","ADAUSDT","AVAXUSDT","SHIBUSDT","DOTUSDT",
    ],
    "binance_url":   "https://api.binance.com/api/v3",
    "ema_hizli":     21,
    "ema_yavas":     55,
    "rsi_periyot":   14,
    "atr_periyot":   14,
    "long_stop_atr":  1.5,
    "long_tp1_atr":   2.0,
    "long_tp2_atr":   3.5,
    "long_tp3_atr":   5.5,
    "short_stop_atr": 1.5,
    "short_tp1_atr":  2.0,
    "short_tp2_atr":  3.5,
    "short_tp3_atr":  5.5,
    "trailing_pct":   0.05,
    "kaldirac":       3,
    "min_puan":       60,
    "tarama_saatleri": ["09:00","15:00","21:00"],
}

# ── ALTIN / GÜMÜŞ ─────────────────────────────────────
METAL = {
    "varliklar": {
        "ALTIN":    "GC=F",    # Gram altın — Kuveyt Türk direkt
        "GUMUS":    "SI=F",    # Gram gümüş — Kuveyt Türk direkt
        "PLATIN":   "PL=F",    # Platin — Kuveyt Türk direkt
        "PALADYUM": "PA=F",    # Paladyum — TEFAS fonu
    },
    "dolar_kur":    "USDTRY=X",
    "ema_hizli":    20,
    "ema_yavas":    50,
    "rsi_periyot":  14,
    "atr_periyot":  14,
    "stop_atr":     1.5,
    "tp1_atr":      2.0,
    "tp2_atr":      3.5,
    "tp3_atr":      6.0,
    "min_puan":     55,
    "tarama_saati": "09:30",
}

# ── BIST HİSSE LİSTESİ (yfinance'de çalışan 207 hisse) ─
BIST_HISSELER = [
    "A1CAP","A1YEN","AAGYO","ACSEL","ADEL","ADESE","ADGYO","AEFES",
    "AFYON","AGESA","AGHOL","AGROT","AGYO","AHGAZ","AHSGY","AKBNK",
    "AKCNS","AKENR","AKFGY","AKFIS","AKFYE","AKGRT","AKHAN","AKMGY",
    "AKSA","AKSEN","AKSGY","AKSUE","AKYHO","ALARK","ALBRK","ALCAR",
    "ALCTL","ALFAS","ALGYO","ALKA","ALKIM","ALKLC","ALTNY","ALVES",
    "ANELE","ANGEN","ANHYT","ANSGR","ARASE","ARCLK","ARDYZ","ARENA",
    "ARFYE","ARMGD","ARSAN","ARTMS","ARZUM","ASELS","ASGYO","ASTOR",
    "ASUZU","ATAGY","ATAKP","ATATP","ATATR","ATEKS","ATLAS","ATSYH",
    "AVGYO","AVHOL","AVOD","AVPGY","AVTUR","AYCES","AYDEM","AYEN",
    "AYES","AYGAZ","AZTEK","BAGFS","BAHKM","BAKAB","BALAT","BALSU",
    "BANVT","BARMA","BASCM","BASGZ","BAYRK","BEGYO","BERA","BESLR",
    "BESTE","BEYAZ","BFREN","BIENY","BIGCH","BIGEN","BIGTK","BIMAS",
    "BINBN","BINHO","BIOEN","BIZIM","BJKAS","BLCYT","BLUME","BMSCH",
    "BMSTL","BNTAS","BOBET","BORLS","BORSK","BOSSA","BRISA","BRKO",
    "BRKSN","BRKVY","BRLSM","BRMEN","BRSAN","BRYAT","BSOKE","BTCIM",
    "BUCIM","BULGS","BURCE","BURVA","BVSAN","BYDNR","CANTE","CASA",
    "CATES","CCOLA","CELHA","CEMAS","CEMTS","CEMZY","CEOEM","CGCAM",
    "CIMSA","CLEBI","CMBTN","CMENT","CONSE","COSMO","CRDFA","CRFSA",
    "CUSAN","CVKMD","CWENE","DAGI","DAPGM","DARDL","DCTTR","DENGE",
    "DERHL","DERIM","DESA","DESPC","DEVA","DGATE","DGGYO","DGNMO",
    "DIRIT","DITAS","DMRGD","DMSAS","DNISI","DOAS","DOCO","DOFER",
    "DOFRB","DOGUB","DOHOL","DOKTA","DSTKF","DUNYH","DURDO","DURKN",
    "DYOBY","DZGYO","EBEBK","ECILC","ECOGR","ECZYT","EDATA","EDIP",
    "EFOR","EGEEN","EGEGY","EGEPO","EGGUB","EGPRO","EGSER","EKGYO",
    "EKIZ","EKOS","EKSUN","ELITE","EMKEL","EMNIS","EMPAE","ENDAE",
    "ENERY","ENJSA","ENKAI","ENPRA","ENSRI","ENTRA","EPLAS","ERBOS",
    "ERCB","EREGL","ERSU","ESCAR","ESCOM","ESEN","ETILR","ETYAT",
    "EUHOL","EUKYO","EUPWR","EUREN","EUYO","EYGYO","FADE","FENER",
    "FLAP","FMIZP","FONET","FORMT","FORTE","FRIGO","FRMPL","FROTO",
    "FZLGY","GARAN","GARFA","GATEG","GEDIK","GEDZA","GENIL","GENKM",
    "GENTS","GEREL","GESAN","GIPTA","GLBMD","GLCVY","GLDTR","GLRMK",
    "GLRYH","GLYHO","GMSTR","GMTAS","GOKNR","GOLTS","GOODY","GOZDE",
    "GRNYO","GRSEL","GRTHO","GSDDE","GSDHO","GSRAY","GUBRF","GUNDG",
    "GWIND","GZNMI","HALKB","HATEK","HATSN","HDFGS","HEDEF","HEKTS",
    "HKTM","HLGYO","HOROZ","HRKET","HTTBT","HUBVC","HUNER","HURGZ",
    "ICBCT","ICUGS","IDGYO","IEYHO","IHAAS","IHEVA","IHGZT","IHLAS",
    "IHLGM","IHYAY","IMASM","INDES","INFO","INGRM","INTEK","INTEM",
    "INVEO","INVES","ISBIR","ISBTR","ISCTR","ISDMR","ISFIN","ISGLK",
    "ISGSY","ISGYO","ISKPL","ISMEN","ISSEN","ISYAT","IZENR","IZFAS",
    "IZINV","IZMDC","JANTS","KAPLM","KAREL","KARSN","KARTN","KATMR",
    "KAYSE","KBORU","KCAER","KCHOL","KENT","KERVN","KFEIN","KGYO",
    "KIMMR","KLGYO","KLKIM","KLMSN","KLNMA","KLRHO","KLSER","KLSYN",
    "KLYPV","KMPUR","KNFRT","KOCMT","KONKA","KONTR","KONYA","KOPOL",
    "KORDS","KOTON","KRDMA","KRDMB","KRDMD","KRGYO","KRONT","KRPLS",
    "KRSTL","KRTEK","KRVGD","KSTUR","KTLEV","KTSKR","KUTPO","KUVVA",
    "KUYAS","KZBGY","KZGYO","LIDER","LIDFA","LILAK","LINK","LKMNH",
    "LMKDC","LOGO","LRSHO","LUKSK","LXGYO","LYDHO","LYDYE","MAALT",
    "MACKO","MAGEN","MAKIM","MAKTK","MANAS","MARBL","MARKA","MARMR",
    "MARTI","MAVI","MCARD","MEDTR","MEGAP","MEGMT","MEKAG","MEPET",
    "MERCN","MERIT","MERKO","METRO","MEYSU","MGROS","MHRGY","MIATK",
    "MMCAS","MNDRS","MNDTR","MOBTL","MOGAN","MOPAS","MPARK","MRGYO",
    "MRSHL","MSGYO","MTRKS","MTRYO","MZHLD","NATEN","NETAS","NETCD",
    "NIBAS","NTGAZ","NTHOL","NUGYO","NUHCM","OBAMS","OBASE","ODAS",
    "ODINE","OFSYM","ONCSM","ONRYT","ORCAY","ORGE","ORMA","OSMEN",
    "OSTIM","OTKAR","OTTO","OYAKC","OYAYO","OYLUM","OYYAT","OZATD",
    "OZGYO","OZKGY","OZRDN","OZSUB","OZYSR","PAGYO","PAHOL","PAMEL",
    "PAPIL","PARSN","PASEU","PATEK","PCILT","PEKGY","PENGD","PENTA",
    "PETKM","PETUN","PGSUS","PINSU","PKART","PKENT","PLTUR","PNLSN",
    "PNSUT","POLHO","POLTK","PRDGS","PRKAB","PRKME","PRZMA","PSDTC",
    "PSGYO","QNBFK","QNBTR","QTEMZ","QUAGR","RALYH","RAYSG","REEDR",
    "RGYAS","RNPOL","RODRG","RTALB","RUBNS","RUZYE","RYGYO","RYSAS",
    "SAFKR","SAHOL","SAMAT","SANEL","SANFM","SANKO","SARKY","SASA",
    "SAYAS","SDTTR","SEGMN","SEGYO","SEKFK","SEKUR","SELEC","SELVA",
    "SERNT","SEYKM","SILVR","SISE","SKBNK","SKTAS","SKYLP","SKYMD",
    "SMART","SMRTG","SMRVA","SNGYO","SNICA","SNPAM","SODSN","SOKE",
    "SOKM","SONME","SRVGY","SUMAS","SUNTK","SURGY","SUWEN","SVGYO",
    "TABGD","TARKM","TATEN","TATGD","TAVHL","TBORG","TCELL","TCKRC",
    "TDGYO","TEHOL","TEKTU","TERA","TEZOL","TGSAS","THYAO","TKFEN",
    "TKNSA","TLMAN","TMPOL","TMSN","TNZTP","TOASO","TRCAS","TRENJ",
    "TRGYO","TRHOL","TRILC","TRMET","TSGYO","TSKB","TSPOR","TTKOM",
    "TTRAK","TUCLK","TUKAS","TUPRS","TUREX","TURGG","TURSG","UCAYM",
    "UFUK","ULAS","ULKER","ULUFA","ULUSE","ULUUN","UNLU","USAK",
    "VAKBN","VAKFA","VAKFN","VAKKO","VANGD","VBTYZ","VERTU","VERUS",
    "VESBE","VESTL","VKFYO","VKGYO","VKING","VRGYO","VSNMD","YAPRK",
    "YATAS","YAYLA","YBTAS","YEOTK","YESIL","YGGYO","YIGIT","YKBNK",
    "YKSLN","YONGA","YUNSA","YYAPI","YYLGD","ZEDUR","ZERGY","ZOREN",
]
