from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    preferences: Mapped[Optional["UserPreference"]] = relationship(back_populates="user", uselist=False)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    discovery_bias: Mapped[float] = mapped_column(Float, default=0.5)
    explicit_genres: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    extras: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship(back_populates="preferences")


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(512), index=True)
    musicbrainz_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(512), index=True)
    artist_id: Mapped[Optional[str]] = mapped_column(ForeignKey("artists.id"), nullable=True)
    release_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    musicbrainz_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    artwork_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(512), index=True)
    album_id: Mapped[Optional[str]] = mapped_column(ForeignKey("albums.id"), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    isrc: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    musicbrainz_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    artwork_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    genres: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    providers: Mapped[list["TrackProvider"]] = relationship(back_populates="track")


class TrackProvider(Base):
    __tablename__ = "track_providers"
    __table_args__ = (UniqueConstraint("provider", "provider_track_id", name="uq_provider_track"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64))  # open | user_owned | apple_music | ...
    provider_track_id: Mapped[str] = mapped_column(String(255))
    playback_type: Mapped[str] = mapped_column(String(64), default="stream")  # stream | progressive | sdk
    availability: Mapped[str] = mapped_column(String(32), default="available")
    territory: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    stream_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    track: Mapped["Track"] = relationship(back_populates="providers")


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    collaborative: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    __table_args__ = (UniqueConstraint("playlist_id", "position", name="uq_playlist_pos"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    playlist_id: Mapped[str] = mapped_column(ForeignKey("playlists.id"), index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    added_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "track_id", name="uq_user_track_like"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    polarity: Mapped[int] = mapped_column(Integer, default=1)  # 1 like, -1 dislike
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlayEvent(Base):
    __tablename__ = "play_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    position_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
