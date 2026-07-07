import React, { useEffect, useState } from "react";

import Link from "@/components/Link";
import TimeAgo from "@/components/TimeAgo";
import BigMessage from "@/components/BigMessage";
import { currentUser } from "@/services/auth";
import Community, { getCategoryMeta } from "@/services/community";

import HomeSection from "./HomeSection";

import "@/pages/community/Community.less";

const PREVIEW_LIMIT = 3;

function CommunityPreview() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentUser.hasPermission("list_community_posts")) {
      setLoading(false);
      return undefined;
    }

    setLoading(true);
    Community.list({ limit: PREVIEW_LIMIT })
      .then(setPosts)
      .finally(() => setLoading(false));
    return undefined;
  }, []);

  if (!currentUser.hasPermission("list_community_posts")) {
    return null;
  }

  const canCreate = currentUser.hasPermission("create_community_post");

  const emptyState = (
    <BigMessage icon="fa-comments" className="home-section-empty home-section-empty--compact">
      <span>
        Start a team discussion about queries and dashboards.{" "}
        {canCreate && <Link href="community/new">Create a post</Link>}
      </span>
    </BigMessage>
  );

  return (
    <HomeSection title="Community" viewAllHref="community" loading={loading}>
      {!loading && posts.length > 0 && (
        <div className="community-preview-list">
          {posts.map(post => {
            const meta = getCategoryMeta(post.category);
            return (
              <Link key={post.id} className="community-preview-item" href={`community/${post.id}`}>
                <span className="community-preview-item__icon">
                  <i className={`fa ${meta.icon}`} aria-hidden="true" />
                </span>
                <span className="community-preview-item__content">
                  <span className="community-preview-item__title">{post.title}</span>
                  <span className="community-preview-item__meta">
                    {meta.label} · {post.user.name} · <TimeAgo date={post.updated_at || post.created_at} />
                  </span>
                </span>
              </Link>
            );
          })}
        </div>
      )}
      {!loading && !posts.length && emptyState}
    </HomeSection>
  );
}

export default CommunityPreview;
