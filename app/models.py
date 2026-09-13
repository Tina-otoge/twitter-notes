from datetime import datetime

import sqlalchemy
from sqlalchemy import (
    ForeignKey,
    ForeignKeyConstraint,
    MetaData,
    String,
    UniqueConstraint,
    orm,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return (
            "".join(
                f"_{character.lower()}" if character.isupper() else character
                for character in cls.__name__
            ).lstrip("_")
            + "s"
        )

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    id: Mapped[str] = orm.mapped_column(String, primary_key=True)
    username: Mapped[str] = orm.mapped_column(String)


class ApiToken(Base):
    id: Mapped[int] = orm.mapped_column(primary_key=True)
    owner_id: Mapped[str] = orm.mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = orm.mapped_column(String, default="")
    digest: Mapped[str] = orm.mapped_column(String, unique=True)
    prefix: Mapped[str] = orm.mapped_column(String)
    created_at: Mapped[datetime] = orm.mapped_column(
        server_default=sqlalchemy.func.current_timestamp()
    )


class Tag(Base):
    __table_args__ = (
        UniqueConstraint("owner_id", "name"),
        UniqueConstraint("owner_id", "id"),
    )

    id: Mapped[int] = orm.mapped_column(primary_key=True)
    owner_id: Mapped[str] = orm.mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = orm.mapped_column(String(collation="NOCASE"))
    color: Mapped[str] = orm.mapped_column(String)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "color": self.color}


class Note(Base):
    owner_id: Mapped[str] = orm.mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = orm.mapped_column(String, primary_key=True)
    username: Mapped[str] = orm.mapped_column(String)
    body: Mapped[str] = orm.mapped_column(String, default="", server_default="")
    updated_at: Mapped[datetime] = orm.mapped_column(
        server_default=sqlalchemy.func.current_timestamp(),
        onupdate=sqlalchemy.func.current_timestamp(),
    )
    tags: Mapped[list[Tag]] = orm.relationship(
        secondary="note_tags",
        viewonly=True,
        lazy="selectin",
        order_by="Tag.name",
    )

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "body": self.body,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "tags": [tag.to_dict() for tag in self.tags],
        }


class NoteTag(Base):
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "user_id"],
            ["notes.owner_id", "notes.user_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["owner_id", "tag_id"],
            ["tags.owner_id", "tags.id"],
            ondelete="CASCADE",
        ),
    )

    owner_id: Mapped[str] = orm.mapped_column(String, primary_key=True)
    user_id: Mapped[str] = orm.mapped_column(String, primary_key=True)
    tag_id: Mapped[int] = orm.mapped_column(primary_key=True)
