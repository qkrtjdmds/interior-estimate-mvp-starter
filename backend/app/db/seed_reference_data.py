from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.reference import Category, Item, Option

SeedData = list[dict[str, Any]]


@dataclass(frozen=True)
class SeedSummary:
    categories_created: int = 0
    categories_skipped: int = 0
    items_created: int = 0
    items_skipped: int = 0
    options_created: int = 0
    options_skipped: int = 0

    def add(self, **changes: int) -> "SeedSummary":
        values = self.__dict__ | changes
        return SeedSummary(**values)


REFERENCE_DATA: SeedData = [
    {
        "name": "도배",
        "description": "벽면 마감재를 새로 시공하는 공정입니다.",
        "sort_order": 10,
        "items": [
            {
                "name": "벽지 시공",
                "description": "공간의 벽면에 벽지를 시공합니다.",
                "sort_order": 10,
                "options": [
                    {
                        "name": "합지벽지",
                        "description": "기본 벽지 시공에 적합한 경제형 옵션입니다.",
                        "unit": "평",
                        "default_price": Decimal("30000"),
                        "recommended": False,
                        "sort_order": 10,
                    },
                    {
                        "name": "실크벽지",
                        "description": "내구성과 마감감이 좋은 추천 벽지 옵션입니다.",
                        "unit": "평",
                        "default_price": Decimal("45000"),
                        "recommended": True,
                        "sort_order": 20,
                    },
                ],
            }
        ],
    },
    {
        "name": "바닥",
        "description": "장판과 마루 등 바닥 마감 공정입니다.",
        "sort_order": 20,
        "items": [
            {
                "name": "장판 시공",
                "description": "주거 공간에 장판을 시공합니다.",
                "sort_order": 10,
                "options": [
                    {
                        "name": "1.8T 장판",
                        "description": "기본 두께의 실속형 장판 옵션입니다.",
                        "unit": "평",
                        "default_price": Decimal("30000"),
                        "recommended": False,
                        "sort_order": 10,
                    },
                    {
                        "name": "2.2T 장판",
                        "description": "두께감과 보행감이 좋은 추천 장판 옵션입니다.",
                        "unit": "평",
                        "default_price": Decimal("40000"),
                        "recommended": True,
                        "sort_order": 20,
                    },
                ],
            },
            {
                "name": "마루 시공",
                "description": "거실과 방 바닥에 마루를 시공합니다.",
                "sort_order": 20,
                "options": [
                    {
                        "name": "강화마루",
                        "description": "표면 강도가 좋은 일반 마루 옵션입니다.",
                        "unit": "평",
                        "default_price": Decimal("70000"),
                        "recommended": False,
                        "sort_order": 10,
                    },
                    {
                        "name": "강마루",
                        "description": "습기와 생활 충격에 강한 추천 마루 옵션입니다.",
                        "unit": "평",
                        "default_price": Decimal("95000"),
                        "recommended": True,
                        "sort_order": 20,
                    },
                ],
            },
        ],
    },
    {
        "name": "도장",
        "description": "벽과 천장 등에 페인트를 칠하는 공정입니다.",
        "sort_order": 30,
        "items": [
            {
                "name": "실내 도장",
                "description": "실내 벽면과 천장에 페인트를 시공합니다.",
                "sort_order": 10,
                "options": [
                    {
                        "name": "일반 수성페인트",
                        "description": "실내 도장에 널리 쓰이는 기본 추천 옵션입니다.",
                        "unit": "평",
                        "default_price": Decimal("25000"),
                        "recommended": True,
                        "sort_order": 10,
                    },
                    {
                        "name": "친환경 페인트",
                        "description": "냄새와 유해물질 부담을 줄인 페인트 옵션입니다.",
                        "unit": "평",
                        "default_price": Decimal("35000"),
                        "recommended": False,
                        "sort_order": 20,
                    },
                ],
            }
        ],
    },
    {
        "name": "전기·조명",
        "description": "조명과 전기 부속을 교체하는 공정입니다.",
        "sort_order": 40,
        "items": [
            {
                "name": "조명 교체",
                "description": "기존 조명을 새 조명으로 교체합니다.",
                "sort_order": 10,
                "options": [
                    {
                        "name": "기본 LED등",
                        "description": "효율이 좋은 기본 LED 조명 교체 옵션입니다.",
                        "unit": "개",
                        "default_price": Decimal("50000"),
                        "recommended": True,
                        "sort_order": 10,
                    },
                    {
                        "name": "디자인 조명",
                        "description": "공간 분위기를 살리는 장식형 조명 옵션입니다.",
                        "unit": "개",
                        "default_price": Decimal("120000"),
                        "recommended": False,
                        "sort_order": 20,
                    },
                ],
            },
            {
                "name": "콘센트 교체",
                "description": "노후 콘센트나 스위치류를 교체합니다.",
                "sort_order": 20,
                "options": [
                    {
                        "name": "일반 콘센트",
                        "description": "기본형 콘센트 교체 옵션입니다.",
                        "unit": "개",
                        "default_price": Decimal("20000"),
                        "recommended": True,
                        "sort_order": 10,
                    }
                ],
            },
        ],
    },
    {
        "name": "욕실",
        "description": "욕실 공간을 부분 또는 전체 리모델링하는 공정입니다.",
        "sort_order": 50,
        "items": [
            {
                "name": "욕실 리모델링",
                "description": "욕실 설비와 마감을 교체합니다.",
                "sort_order": 10,
                "options": [
                    {
                        "name": "기본형 욕실 공사",
                        "description": "필수 설비와 마감을 포함한 기본 욕실 공사입니다.",
                        "unit": "식",
                        "default_price": Decimal("3500000"),
                        "recommended": True,
                        "sort_order": 10,
                    },
                    {
                        "name": "고급형 욕실 공사",
                        "description": "고급 자재와 마감 품질을 반영한 욕실 공사입니다.",
                        "unit": "식",
                        "default_price": Decimal("5500000"),
                        "recommended": False,
                        "sort_order": 20,
                    },
                ],
            }
        ],
    },
    {
        "name": "주방",
        "description": "싱크대와 주방 가구를 시공하는 공정입니다.",
        "sort_order": 60,
        "items": [
            {
                "name": "싱크대 시공",
                "description": "주방 크기에 맞춰 싱크대를 설치합니다.",
                "sort_order": 10,
                "options": [
                    {
                        "name": "기본형 싱크대",
                        "description": "일반적인 주방 구성에 맞춘 기본 싱크대입니다.",
                        "unit": "m",
                        "default_price": Decimal("600000"),
                        "recommended": True,
                        "sort_order": 10,
                    },
                    {
                        "name": "고급형 싱크대",
                        "description": "고급 자재와 수납 구성을 반영한 싱크대입니다.",
                        "unit": "m",
                        "default_price": Decimal("900000"),
                        "recommended": False,
                        "sort_order": 20,
                    },
                ],
            }
        ],
    },
    {
        "name": "철거",
        "description": "기존 마감재를 철거하고 폐기하는 공정입니다.",
        "sort_order": 70,
        "items": [
            {
                "name": "기존 마감재 철거",
                "description": "벽지와 바닥재 등 기존 마감재를 제거합니다.",
                "sort_order": 10,
                "options": [
                    {
                        "name": "벽지 철거",
                        "description": "기존 벽지를 제거하는 작업입니다.",
                        "unit": "평",
                        "default_price": Decimal("10000"),
                        "recommended": False,
                        "sort_order": 10,
                    },
                    {
                        "name": "바닥재 철거",
                        "description": "기존 장판이나 마루를 제거하는 작업입니다.",
                        "unit": "평",
                        "default_price": Decimal("20000"),
                        "recommended": False,
                        "sort_order": 20,
                    },
                ],
            }
        ],
    },
]


def normalize_name(name: str) -> str:
    return name.strip().casefold()


def _visibility_values(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": data.get("description"),
        "active": data.get("active", True),
        "customer_visible": data.get("customer_visible", True),
        "sort_order": data.get("sort_order", 0),
    }


def _find_category(db: Session, name: str) -> Category | None:
    normalized = normalize_name(name)
    categories = db.scalars(select(Category)).all()
    return next((category for category in categories if normalize_name(category.name) == normalized), None)


def _find_item(db: Session, category_id: int, name: str) -> Item | None:
    normalized = normalize_name(name)
    items = db.scalars(select(Item).where(Item.category_id == category_id)).all()
    return next((item for item in items if normalize_name(item.name) == normalized), None)


def _find_option(db: Session, item_id: int, name: str) -> Option | None:
    normalized = normalize_name(name)
    options = db.scalars(select(Option).where(Option.item_id == item_id)).all()
    return next((option for option in options if normalize_name(option.name) == normalized), None)


def seed_reference_data(db: Session, seed_data: SeedData = REFERENCE_DATA) -> SeedSummary:
    summary = SeedSummary()
    try:
        with db.begin():
            for category_data in seed_data:
                category = _find_category(db, category_data["name"])
                if category is None:
                    category = Category(
                        name=category_data["name"].strip(),
                        **_visibility_values(category_data),
                    )
                    db.add(category)
                    db.flush()
                    summary = summary.add(categories_created=summary.categories_created + 1)
                else:
                    summary = summary.add(categories_skipped=summary.categories_skipped + 1)

                for item_data in category_data.get("items", []):
                    item = _find_item(db, category.id, item_data["name"])
                    if item is None:
                        item = Item(
                            category_id=category.id,
                            name=item_data["name"].strip(),
                            **_visibility_values(item_data),
                        )
                        db.add(item)
                        db.flush()
                        summary = summary.add(items_created=summary.items_created + 1)
                    else:
                        summary = summary.add(items_skipped=summary.items_skipped + 1)

                    for option_data in item_data.get("options", []):
                        option = _find_option(db, item.id, option_data["name"])
                        if option is None:
                            option = Option(
                                item_id=item.id,
                                name=option_data["name"].strip(),
                                description=option_data.get("description"),
                                unit=option_data["unit"].strip(),
                                default_price=option_data["default_price"],
                                recommended=option_data.get("recommended", False),
                                active=option_data.get("active", True),
                                customer_visible=option_data.get("customer_visible", True),
                                sort_order=option_data.get("sort_order", 0),
                            )
                            db.add(option)
                            db.flush()
                            summary = summary.add(options_created=summary.options_created + 1)
                        else:
                            summary = summary.add(options_skipped=summary.options_skipped + 1)
        return summary
    except Exception:
        db.rollback()
        raise


def print_summary(summary: SeedSummary) -> None:
    print(f"categories created={summary.categories_created} skipped={summary.categories_skipped}")
    print(f"items created={summary.items_created} skipped={summary.items_skipped}")
    print(f"options created={summary.options_created} skipped={summary.options_skipped}")


def main() -> None:
    with SessionLocal() as db:
        summary = seed_reference_data(db)
    print_summary(summary)


if __name__ == "__main__":
    main()