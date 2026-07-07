import React, { useEffect, useState } from "react";

import Button from "antd/lib/button";
import Form from "antd/lib/form";
import Input from "antd/lib/input";
import Modal from "antd/lib/modal";
import Select from "antd/lib/select";

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

  useEffect(() => {
    setLoading(true);
    Community.get(postId)
      .then(data => {
        setPost(data);
        form.setFieldsValue({
          title: data.title,
          category: data.category,
          body: data.body,
        });
      })
      .catch(err => onError(err))
      .finally(() => setLoading(false));
  }, [form, onError, postId]);

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
    Modal.confirm({
      title: "Delete this post?",
      content: "This cannot be undone.",
      okType: "danger",
      onOk: () =>
        Community.delete(postId)
          .then(() => {
            notification.success("Post deleted.");
            navigateTo("community");
          })
          .catch(() => notification.error("Failed to delete post.")),
    });
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
        <Form form={form} layout="vertical" onFinish={handleSave}>
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
      ) : (
        <article className="community-post-view">
          <div className="community-post-view__meta">
            <span className="community-post-view__category">
              <i className={`fa ${categoryMeta.icon} m-r-5`} aria-hidden="true" />
              {categoryMeta.label}
            </span>
            <img
              className="profile__image_thumb community-post-view__avatar"
              src={post.user.profile_image_url}
              alt=""
            />
            <span>{post.user.name}</span>
            <TimeAgo date={post.updated_at || post.created_at} />
          </div>
          <div className="community-post-view__body">{post.body}</div>
        </article>
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
