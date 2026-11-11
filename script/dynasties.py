"""Build ruling dynasties catalog and entity files.

Output:
1. data/entities/dynasties/<id>.json
2. data/dist/catalog/dynasties-index.json
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DYNASTIES_DIR = DATA_DIR / "entities" / "dynasties"
DIST_SPATIAL_DIR = BASE_DIR / "data" / "dist" / "spatial"
DIST_CATALOG_DIR = BASE_DIR / "data" / "dist" / "catalog"

# ruling dynasties of vietnam
DYNASTIES = [
    {
        "id": "hong-bang",
        "state_id": "van-lang",
        "names": {
            "canonical": {
                "vi": "Họ Hồng Bàng (Thời đại Hùng Vương)",
                "en": "Hong Bang dynasty (Era of Hung Kings)",
                "zh-CN": "鸿庞氏 (雄王时代)",
                "ja": "鴻龐氏 (雄王時代)"
            }
        },
        "from_year": -700,
        "to_year": -258,
        "capital": "phong-chau",
        "source_ids": ["src-dai-viet", "src-dao-duy-anh"]
    },
    {
        "id": "thuc",
        "state_id": "au-lac",
        "names": {
            "canonical": {
                "vi": "Nhà Thục (Thục Phán An Dương Vương)",
                "en": "Thuc dynasty (An Duong Vuong)",
                "zh-CN": "蜀朝 (安阳王)",
                "ja": "蜀朝 (安陽王)"
            }
        },
        "from_year": -257,
        "to_year": -179,
        "capital": "co-loa",
        "source_ids": ["src-dai-viet", "src-shiji", "src-dao-duy-anh"]
    },
    {
        "id": "trieu",
        "state_id": "nam-viet",
        "names": {
            "canonical": {
                "vi": "Nhà Triệu (Triệu triều)",
                "en": "Zhao dynasty of Nanyue",
                "zh-CN": "赵朝 (南越国)",
                "ja": "趙朝 (南越国)"
            }
        },
        "from_year": -204,
        "to_year": -111,
        "capital": "panyu",
        "source_ids": ["src-shiji", "src-dai-viet"]
    },
    {
        "id": "tien-ly",
        "state_id": "van-xuan",
        "names": {
            "canonical": {
                "vi": "Nhà Tiền Lý (Lý Bí / Lý Nam Đế)",
                "en": "Early Ly dynasty",
                "zh-CN": "前李朝 (李贲)",
                "ja": "前李朝"
            }
        },
        "from_year": 544,
        "to_year": 602,
        "capital": "long-bien",
        "source_ids": ["src-dai-viet", "src-dao-duy-anh"]
    },
    {
        "id": "dinh",
        "state_id": "dai-co-viet",
        "names": {
            "canonical": {
                "vi": "Nhà Đinh (Đinh Tiên Hoàng)",
                "en": "Dinh dynasty",
                "zh-CN": "丁朝 (丁部领)",
                "ja": "丁朝"
            }
        },
        "from_year": 968,
        "to_year": 980,
        "capital": "hoa-lu",
        "source_ids": ["src-dai-viet"]
    },
    {
        "id": "tien-le",
        "state_id": "dai-co-viet",
        "names": {
            "canonical": {
                "vi": "Nhà Tiền Lê (Lê Đại Hành)",
                "en": "Early Le dynasty",
                "zh-CN": "前黎朝 (黎桓)",
                "ja": "前黎朝"
            }
        },
        "from_year": 980,
        "to_year": 1009,
        "capital": "hoa-lu",
        "source_ids": ["src-dai-viet"]
    },
    {
        "id": "ly",
        "state_id": "đại-việt",
        "names": {
            "canonical": {
                "vi": "Nhà Lý (Triều Lý)",
                "en": "Ly dynasty",
                "zh-CN": "李朝",
                "ja": "李朝"
            }
        },
        "from_year": 1009,
        "to_year": 1225,
        "capital": "thang-long",
        "source_ids": ["src-dai-viet", "src-dao-duy-anh"]
    },
    {
        "id": "tran",
        "state_id": "đại-việt",
        "names": {
            "canonical": {
                "vi": "Nhà Trần (Triều Trần)",
                "en": "Tran dynasty",
                "zh-CN": "陈朝",
                "ja": "陳朝"
            }
        },
        "from_year": 1225,
        "to_year": 1400,
        "capital": "thang-long",
        "source_ids": ["src-dai-viet"]
    },
    {
        "id": "ho",
        "state_id": "dai-ngu",
        "names": {
            "canonical": {
                "vi": "Nhà Hồ (Hồ Quý Ly)",
                "en": "Ho dynasty",
                "zh-CN": "胡朝",
                "ja": "胡朝"
            }
        },
        "from_year": 1400,
        "to_year": 1407,
        "capital": "tay-do",
        "source_ids": ["src-dai-viet"]
    },
    {
        "id": "hau-le",
        "state_id": "đại-việt",
        "names": {
            "canonical": {
                "vi": "Nhà Hậu Lê (Lê Sơ & Lê Trung Hưng)",
                "en": "Later Le dynasty",
                "zh-CN": "后黎朝",
                "ja": "後黎朝"
            }
        },
        "from_year": 1428,
        "to_year": 1789,
        "capital": "thang-long",
        "source_ids": ["src-dai-viet"]
    },
    {
        "id": "tay-son",
        "state_id": "đại-việt",
        "names": {
            "canonical": {
                "vi": "Nhà Tây Sơn (Quang Trung - Nguyễn Huệ)",
                "en": "Tay Son dynasty",
                "zh-CN": "西山朝",
                "ja": "西山朝"
            }
        },
        "from_year": 1778,
        "to_year": 1802,
        "capital": "phu-xuan-hue",
        "source_ids": ["src-dai-nam"]
    },
    {
        "id": "nguyen",
        "state_id": "dai-nam",
        "names": {
            "canonical": {
                "vi": "Nhà Nguyễn (Triều Nguyễn)",
                "en": "Nguyen dynasty",
                "zh-CN": "阮朝",
                "ja": "阮朝"
            }
        },
        "from_year": 1802,
        "to_year": 1945,
        "capital": "phu-xuan-hue",
        "source_ids": ["src-dai-nam", "src-dao-duy-anh"]
    }
]

def main():
    DYNASTIES_DIR.mkdir(parents=True, exist_ok=True)
    DIST_CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    # export individual dynasty entity files
    for dyn in DYNASTIES:
        p = DYNASTIES_DIR / f"{dyn['id']}.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(dyn, f, ensure_ascii=False, indent=2)

    # export dynasties catalog index
    with open(DIST_CATALOG_DIR / "dynasties-index.json", "w", encoding="utf-8") as f:
        json.dump(DYNASTIES, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(DYNASTIES)} dynasties.")

if __name__ == "__main__":
    main()
