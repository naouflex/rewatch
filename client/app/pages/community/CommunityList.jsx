import React, { useCallback, useEffect, useMemo, useState } from "react";

import Button from "antd/lib/button";
import Input from "antd/lib/input";
import Tag from "antd/lib/tag";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import Link from "@/components/Link";
import PageHeader from "@/components/PageHeader";
import TimeAgo from "@/components/TimeAgo";
import BigMessage from "@/components/BigMessage";
import { currentUser } from "@/services/auth";
import Community, { COMMUNITY_CATEGORIES, getCategoryMeta } from "@/services/community";
import routes from "@/services/routes";

import "./Community.less";

const { Search } = Input;

function CategoryBadge({ category }) {
  const meta = getCategoryMeta(category);
  return (
    <Tag className="community-category-tag">
      <i className={`fa ${meta.icon} m-r-5`} aria-hidden="true" />
      {meta.label}
    </Tag>
  );
}

function PostCard({ post }) {
  return (
    <Link className="community-post-card" href={`community/${post.id}`}>
      <div className="community-post-card__header">
        <CategoryBadge category={post.category} />
        <TimeAgo date={post.updated_at || post.created_at} />
      </div>
      <h3 className="community-post-card__title">{post.title}</h3>
      {post.excerpt && <p className="community-post-card__excerpt">{post.excerpt}</p>}
      <div className="community-post-card__footer">
        <img
          className="profile__image_thumb community-post-card__avatar"
          src={post.user.profile_image_url}
          alt=""
        />
        <span>{post.user.name}</span>
        <span className="community-post-card__stats">
          <i className="fa fa-comment-o m-r-5" aria-hidden="true" />
          {post.reply_count || 0}
          <span className="community-post-card__stats-sep" />
          <i className="fa fa-thumbs-up m-r-5" aria-hidden="true" />
          {post.like_count || 0}
        </span>
      </div>
    </Link>
  );
}

function CommunityListPage() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");

  const canCreate = currentUser.hasPermission("create_community_post");

  const loadPosts = useCallback(() => {
    setLoading(true);
    Community.list({
      category: category === "all" ? undefined : category,
      q: search || undefined,
    })
      .then(setPosts)
      .finally(() => setLoading(false));
  }, [category, search]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  const filteredLabel = useMemo(() => {
    if (category === "all") {
      return "All discussions";
    }
    return getCategoryMeta(category).label;
  }, [category]);

  return (
    <div className="community-page container">
      <PageHeader
        title="Community"
        description="Discuss queries, dashboards, alerts, and tips with your team."
      >
        {canCreate && (
          <Link.Button type="primary" href="community/new">
            <i className="fa fa-plus m-r-5" aria-hidden="true" />
            New post
          </Link.Button>
        )}
      </PageHeader>

      <div className="community-toolbar">
        <div className="community-toolbar__categories">
          <Button
            type={category === "all" ? "primary" : "default"}
            size="small"
            onClick={() => setCategory("all")}
          >
            All
          </Button>
          {COMMUNITY_CATEGORIES.map(item => (
            <Button
              key={item.value}
              type={category === item.value ? "primary" : "default"}
              size="small"
              onClick={() => setCategory(item.value)}
            >
              <i className={`fa ${item.icon} m-r-5`} aria-hidden="true" />
              {item.label}
            </Button>
          ))}
        </div>
        <Search
          allowClear
          placeholder="Search posts..."
          className="community-toolbar__search"
          onSearch={value => setSearch(value.trim())}
        />
      </div>

      <h2 className="community-section-title">{filteredLabel}</h2>

      {loading ? (
        <div className="community-loading">Loading posts...</div>
      ) : posts.length ? (
        <div className="community-post-grid">
          {posts.map(post => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <BigMessage icon="fa-comments" className="community-empty">
          {search ? "No posts match your search." : "No posts yet — start the conversation!"}
          {canCreate && !search && (
            <>
              {" "}
              <Link href="community/new">Create the first post</Link>
            </>
          )}
        </BigMessage>
      )}
    </div>
  );
}

routes.register(
  "Community.List",
  routeWithUserSession({
    path: "/community",
    title: "Community",
    render: pageProps => <CommunityListPage {...pageProps} />,
  })
);

export default CommunityListPage;
