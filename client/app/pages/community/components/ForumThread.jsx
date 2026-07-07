import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";

import Button from "antd/lib/button";
import Form from "antd/lib/form";
import Input from "antd/lib/input";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";

import TimeAgo from "@/components/TimeAgo";
import { currentUser } from "@/services/auth";
import notification from "@/services/notification";
import Community from "@/services/community";

import ForumLikeButton from "./ForumLikeButton";

const { TextArea } = Input;

function CommentItem({
  comment,
  replies,
  canReply,
  onReply,
  onEdit,
  onDelete,
  onToggleLike,
  replyToId,
  onCancelReply,
  onSubmitReply,
  submittingReply,
}) {
  const [editing, setEditing] = useState(false);
  const [editBody, setEditBody] = useState(comment.body);
  const [saving, setSaving] = useState(false);

  const canEdit =
    currentUser.hasPermission("edit_community_post") &&
    (currentUser.isAdmin || currentUser.id === comment.user_id);

  const handleSaveEdit = () => {
    const body = editBody.trim();
    if (!body) {
      return;
    }
    setSaving(true);
    onEdit(comment.id, body)
      .then(() => {
        setEditing(false);
        notification.success("Reply updated.");
      })
      .catch(() => notification.error("Failed to update reply."))
      .finally(() => setSaving(false));
  };

  const handleDelete = () => {
    confirmDialog({
      title: "Delete this reply?",
      description: "This cannot be undone.",
      variant: "danger",
      onConfirm: () =>
        onDelete(comment.id)
          .then(() => notification.success("Reply deleted."))
          .catch(() => notification.error("Failed to delete reply.")),
    });
  };

  return (
    <div className="forum-comment">
      <div className="forum-comment__header">
        <img className="profile__image_thumb forum-comment__avatar" src={comment.user.profile_image_url} alt="" />
        <div className="forum-comment__meta">
          <strong>{comment.user.name}</strong>
          <TimeAgo date={comment.updated_at || comment.created_at} />
        </div>
        <ForumLikeButton
          size="small"
          count={comment.like_count}
          isLiked={comment.is_liked}
          onToggle={() => onToggleLike(comment.id)}
        />
      </div>

      {editing ? (
        <div className="forum-comment__edit">
          <TextArea rows={4} value={editBody} onChange={e => setEditBody(e.target.value)} />
          <div className="forum-comment__edit-actions">
            <Button type="primary" size="small" loading={saving} onClick={handleSaveEdit}>
              Save
            </Button>
            <Button size="small" onClick={() => setEditing(false)} disabled={saving}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="forum-comment__body">{comment.body}</div>
      )}

      {!editing && (
        <div className="forum-comment__actions">
          {canReply && (
            <Button type="link" size="small" onClick={() => onReply(comment.id)}>
              Reply
            </Button>
          )}
          {canEdit && (
            <>
              <Button type="link" size="small" onClick={() => setEditing(true)}>
                Edit
              </Button>
              <Button type="link" size="small" danger onClick={handleDelete}>
                Delete
              </Button>
            </>
          )}
        </div>
      )}

      {replyToId === comment.id && (
        <Form className="forum-reply-form forum-reply-form--nested" onFinish={values => onSubmitReply(comment.id, values)}>
          <Form.Item name="body" rules={[{ required: true, message: "Write a reply" }]}>
            <TextArea rows={3} placeholder={`Reply to ${comment.user.name}...`} autoFocus />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" size="small" loading={submittingReply} className="m-r-10">
              Reply
            </Button>
            <Button size="small" onClick={onCancelReply} disabled={submittingReply}>
              Cancel
            </Button>
          </Form.Item>
        </Form>
      )}

      {replies?.length > 0 && (
        <div className="forum-comment__replies">
          {replies.map(reply => (
            <CommentItem
              key={reply.id}
              comment={reply}
              canReply={false}
              onEdit={onEdit}
              onDelete={onDelete}
              onToggleLike={onToggleLike}
              onReply={onReply}
              replyToId={replyToId}
              onCancelReply={onCancelReply}
              onSubmitReply={onSubmitReply}
              submittingReply={submittingReply}
            />
          ))}
        </div>
      )}
    </div>
  );
}

CommentItem.propTypes = {
  comment: PropTypes.object.isRequired,
  replies: PropTypes.array,
  canReply: PropTypes.bool,
  onReply: PropTypes.func.isRequired,
  onEdit: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onToggleLike: PropTypes.func.isRequired,
  replyToId: PropTypes.number,
  onCancelReply: PropTypes.func.isRequired,
  onSubmitReply: PropTypes.func.isRequired,
  submittingReply: PropTypes.bool,
};

CommentItem.defaultProps = {
  replies: [],
  canReply: false,
  replyToId: null,
  submittingReply: false,
};

export default function ForumThread({ post, onChange }) {
  const [replyToId, setReplyToId] = useState(null);
  const [submittingReply, setSubmittingReply] = useState(false);
  const [form] = Form.useForm();

  const canReply = currentUser.hasPermission("create_community_post");

  const { topLevel, repliesByParent } = useMemo(() => {
    const comments = post?.comments || [];
    const roots = [];
    const byParent = {};

    comments.forEach(comment => {
      if (comment.parent_id) {
        if (!byParent[comment.parent_id]) {
          byParent[comment.parent_id] = [];
        }
        byParent[comment.parent_id].push(comment);
      } else {
        roots.push(comment);
      }
    });

    return { topLevel: roots, repliesByParent: byParent };
  }, [post]);

  const refreshPost = () => Community.get(post.id).then(onChange);

  const handleTopLevelReply = values => {
    setSubmittingReply(true);
    Community.createComment(post.id, { body: values.body })
      .then(onChange)
      .then(() => {
        form.resetFields();
        notification.success("Reply posted.");
      })
      .catch(() => notification.error("Failed to post reply."))
      .finally(() => setSubmittingReply(false));
  };

  const handleNestedReply = (parentId, values) => {
    setSubmittingReply(true);
    Community.createComment(post.id, { body: values.body, parent_id: parentId })
      .then(onChange)
      .then(() => {
        setReplyToId(null);
        notification.success("Reply posted.");
      })
      .catch(() => notification.error("Failed to post reply."))
      .finally(() => setSubmittingReply(false));
  };

  const handleEdit = (commentId, body) => Community.saveComment(post.id, commentId, { body }).then(onChange);

  const handleDelete = commentId => Community.deleteComment(post.id, commentId).then(onChange);

  const handleToggleCommentLike = commentId =>
    Community.toggleCommentLike(post.id, commentId).then(refreshPost).catch(() => notification.error("Failed to update like."));

  return (
    <section className="forum-thread">
      <div className="forum-thread__header">
        <h3>{topLevel.length ? `${post.reply_count} repl${post.reply_count === 1 ? "y" : "ies"}` : "Replies"}</h3>
      </div>

      {canReply && (
        <Form form={form} className="forum-reply-form" onFinish={handleTopLevelReply}>
          <Form.Item name="body" rules={[{ required: true, message: "Write a reply" }]}>
            <TextArea rows={4} placeholder="Join the discussion..." />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submittingReply}>
              Post reply
            </Button>
          </Form.Item>
        </Form>
      )}

      <div className="forum-thread__comments">
        {topLevel.map(comment => (
          <CommentItem
            key={comment.id}
            comment={comment}
            replies={repliesByParent[comment.id] || []}
            canReply={canReply}
            onReply={setReplyToId}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onToggleLike={handleToggleCommentLike}
            replyToId={replyToId}
            onCancelReply={() => setReplyToId(null)}
            onSubmitReply={handleNestedReply}
            submittingReply={submittingReply}
          />
        ))}
        {!topLevel.length && <p className="forum-thread__empty">No replies yet — be the first to respond.</p>}
      </div>
    </section>
  );
}

ForumThread.propTypes = {
  post: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
};
