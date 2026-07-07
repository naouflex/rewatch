import React, { useEffect, useState } from "react";

import Button from "antd/lib/button";
import Form from "antd/lib/form";
import Input from "antd/lib/input";
import Select from "antd/lib/select";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";
import Link from "@/components/Link";
import PageHeader from "@/components/PageHeader";
import TimeAgo from "@/components/TimeAgo";
import LoadingState from "@/components/items-list/components/LoadingState";
import { currentUser } from "@/services/auth";
import Community, { COMMUNITY_CATEGORIES, getCategoryMeta } from "@/services/community";
import notification from "@/services/notification";
import routes from "@/services/routes";

import ForumLikeButton from "./components/ForumLikeButton";
import ForumThread from "./components/ForumThread";

import "./Community.less";

const { TextArea } = Input;

function CommunityPostPage({ postId, onError }) {
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const canEdit =
    post &&
    currentUser.hasPermission("edit_community_post") &&
    (currentUser.isAdmin || currentUser.id === post.user_id);

  const loadPost = () =>
    Community.get(postId)
      .then(setPost)
      .catch(err => onError(err));

  useEffect(() => {
    setLoading(true);
    loadPost().finally(() => setLoading(false));
  }, [postId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (post) {
      form.setFieldsValue({
        title: post.title,
        category: post.category,
        body: post.body,
      });
    }
  }, [form, post]);

  const handleSave = values => {
    setSaving(true);
    Community.save(postId, values)
      .then(data => {
        setPost(data);
        setEditing(false);
        notification.success("Post updated.");
      })
      .catch(() => notification.error("Failed to update post."))
      .finally(() => setSaving(false));
  };

  const handleDelete = () => {
    confirmDialog({
      title: "Delete this post?",
      description: "This cannot be undone.",
      variant: "danger",
      onConfirm: () =>
        Community.delete(postId)
          .then(() => {
            notification.success("Post deleted.");
            navigateTo("community");
          })
          .catch(() => notification.error("Failed to delete post.")),
    });
  };

  const handleTogglePostLike = () => {
    Community.togglePostLike(postId)
      .then(result => {
        setPost(current => ({ ...current, like_count: result.like_count, is_liked: result.is_liked }));
      })
      .catch(() => notification.error("Failed to update like."));
  };

  if (loading) {
    return <LoadingState className="" />;
  }

  if (!post) {
    return null;
  }

  const categoryMeta = getCategoryMeta(post.category);

  return (
    <div className="community-page container">
      <PageHeader
        title={editing ? "Edit post" : post.title}
        description={
          !editing && (
            <>
              <Link href="community">Community</Link>
              {" / "}
              {categoryMeta.label}
            </>
          )
        }
      >
        {!editing && canEdit && (
          <>
            <Button className="m-r-10" onClick={() => setEditing(true)}>
              Edit
            </Button>
            <Button danger onClick={handleDelete}>
              Delete
            </Button>
          </>
        )}
      </PageHeader>

      {editing ? (
        <div className="community-layout">
          <Form form={form} layout="vertical" className="community-form" onFinish={handleSave}>
            <Form.Item name="title" label="Title" rules={[{ required: true, message: "Title is required" }]}>
              <Input maxLength={255} />
            </Form.Item>
            <Form.Item name="category" label="Category" rules={[{ required: true }]}>
              <Select>
                {COMMUNITY_CATEGORIES.map(item => (
                  <Select.Option key={item.value} value={item.value}>
                    {item.label}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="body" label="Body" rules={[{ required: true, message: "Body is required" }]}>
              <TextArea rows={12} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={saving} className="m-r-10">
                Save
              </Button>
              <Button onClick={() => setEditing(false)} disabled={saving}>
                Cancel
              </Button>
            </Form.Item>
          </Form>
        </div>
      ) : (
        <div className="community-layout">
          <article className="community-post-view">
            <div className="community-post-view__meta">
              <span className="community-post-view__category">
                <i className={`fa ${categoryMeta.icon} m-r-5`} aria-hidden="true" />
                {categoryMeta.label}
              </span>
              <span className="community-post-view__author">
                <img
                  className="profile__image_thumb community-post-view__avatar"
                  src={post.user.profile_image_url}
                  alt=""
                />
                {post.user.name}
              </span>
              <TimeAgo date={post.updated_at || post.created_at} />
              <ForumLikeButton
                count={post.like_count}
                isLiked={post.is_liked}
                onToggle={handleTogglePostLike}
              />
            </div>
            <div className="community-post-view__body">{post.body}</div>
          </article>
          <ForumThread post={post} onChange={setPost} />
        </div>
      )}
    </div>
  );
}

routes.register(
  "Community.View",
  routeWithUserSession({
    path: "/community/:postId",
    title: "Community post",
    render: pageProps => <CommunityPostPage {...pageProps} />,
  })
);

export default CommunityPostPage;
