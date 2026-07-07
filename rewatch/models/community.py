"""Community forum posts for org-wide discussions."""

from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import backref

from rewatch.models.base import Column, db, key_type, primary_key
from rewatch.models.mixins import BelongsToOrgMixin, TimestampMixin

FORUM_CATEGORIES = ("general", "queries", "dashboards", "alerts", "tips")
FORUM_LIKE_POST = "post"
FORUM_LIKE_COMMENT = "comment"


class ForumPost(TimestampMixin, BelongsToOrgMixin, db.Model):
    __tablename__ = "forum_posts"

    id = primary_key("ForumPost")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(key_type("User"), db.ForeignKey("users.id"), nullable=False, index=True)
    title = Column(db.String(255), nullable=False)
    body = Column(db.Text, nullable=False)
    category = Column(db.String(32), nullable=False, default="general", index=True)

    user = db.relationship(
        "User",
        backref=backref("forum_posts", lazy="dynamic"),
        foreign_keys=[user_id],
    )
    org = db.relationship(
        "Organization",
        backref=backref("forum_posts", lazy="dynamic"),
        foreign_keys=[org_id],
    )
    comments = db.relationship(
        "ForumComment",
        backref="post",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="ForumComment.created_at",
    )

    @classmethod
    def all_for_org(cls, org, category=None, q=None):
        query = cls.query.filter(cls.org == org).order_by(cls.updated_at.desc())
        if category:
            query = query.filter(cls.category == category)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter(db.or_(cls.title.ilike(pattern), cls.body.ilike(pattern)))
        return query


class ForumComment(TimestampMixin, BelongsToOrgMixin, db.Model):
    __tablename__ = "forum_comments"

    id = primary_key("ForumComment")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"), nullable=False, index=True)
    post_id = Column(key_type("ForumPost"), db.ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(key_type("User"), db.ForeignKey("users.id"), nullable=False, index=True)
    parent_id = Column(
        key_type("ForumComment"),
        db.ForeignKey("forum_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    body = Column(db.Text, nullable=False)

    user = db.relationship(
        "User",
        backref=backref("forum_comments", lazy="dynamic"),
        foreign_keys=[user_id],
    )
    org = db.relationship(
        "Organization",
        backref=backref("forum_comments", lazy="dynamic"),
        foreign_keys=[org_id],
    )

    @classmethod
    def for_post(cls, post_id):
        return cls.query.filter(cls.post_id == post_id).order_by(cls.created_at.asc())


class ForumLike(TimestampMixin, db.Model):
    __tablename__ = "forum_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="unique_forum_like"),
    )

    id = primary_key("ForumLike")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(key_type("User"), db.ForeignKey("users.id"), nullable=False, index=True)
    target_type = Column(db.String(16), nullable=False, index=True)
    target_id = Column(db.Integer, nullable=False, index=True)

    user = db.relationship("User", backref=backref("forum_likes", lazy="dynamic"))

    @classmethod
    def count_for(cls, target_type, target_id):
        return cls.query.filter(cls.target_type == target_type, cls.target_id == target_id).count()

    @classmethod
    def is_liked(cls, user_id, target_type, target_id):
        if not user_id:
            return False
        return (
            cls.query.filter(
                cls.user_id == user_id,
                cls.target_type == target_type,
                cls.target_id == target_id,
            ).count()
            > 0
        )

    @classmethod
    def summaries(cls, user_id, target_type, target_ids):
        if not target_ids:
            return {}

        from sqlalchemy import func

        counts = dict(
            db.session.query(cls.target_id, func.count(cls.id))
            .filter(cls.target_type == target_type, cls.target_id.in_(target_ids))
            .group_by(cls.target_id)
            .all()
        )

        liked_ids = set()
        if user_id:
            liked_ids = {
                row.target_id
                for row in cls.query.filter(
                    cls.user_id == user_id,
                    cls.target_type == target_type,
                    cls.target_id.in_(target_ids),
                )
            }

        return {
            target_id: {
                "like_count": counts.get(target_id, 0),
                "is_liked": target_id in liked_ids,
            }
            for target_id in target_ids
        }

    @classmethod
    def toggle(cls, user, org, target_type, target_id):
        existing = cls.query.filter(
            cls.user_id == user.id,
            cls.target_type == target_type,
            cls.target_id == target_id,
        ).one_or_none()

        if existing:
            db.session.delete(existing)
            liked = False
        else:
            db.session.add(
                cls(
                    user_id=user.id,
                    org_id=org.id,
                    target_type=target_type,
                    target_id=target_id,
                )
            )
            liked = True

        db.session.commit()
        return {"is_liked": liked, "like_count": cls.count_for(target_type, target_id)}
