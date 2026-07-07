"""Community forum posts for org-wide discussions."""

from __future__ import annotations

from sqlalchemy.orm import backref

from rewatch.models.base import Column, db, key_type, primary_key
from rewatch.models.mixins import BelongsToOrgMixin, TimestampMixin

FORUM_CATEGORIES = ("general", "queries", "dashboards", "alerts", "tips")


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

    @classmethod
    def all_for_org(cls, org, category=None, q=None):
        query = cls.query.filter(cls.org == org).order_by(cls.updated_at.desc())
        if category:
            query = query.filter(cls.category == category)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter(db.or_(cls.title.ilike(pattern), cls.body.ilike(pattern)))
        return query
