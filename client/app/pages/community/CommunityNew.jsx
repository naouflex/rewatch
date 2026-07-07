import React, { useEffect, useState } from "react";

import Button from "antd/lib/button";
import Form from "antd/lib/form";
import Input from "antd/lib/input";
import Select from "antd/lib/select";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";
import Link from "@/components/Link";
import CreatePageLayout from "@/components/items-list/CreatePageLayout";
import { currentUser } from "@/services/auth";
import Community, { COMMUNITY_CATEGORIES } from "@/services/community";
import notification from "@/services/notification";
import routes from "@/services/routes";

import "@/components/items-list/create-page-layout.less";
import "./Community.less";

const { TextArea } = Input;

function CommunityNewPage() {
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const canCreate = currentUser.hasPermission("create_community_post");

  useEffect(() => {
    if (!canCreate) {
      navigateTo("community", true);
    }
  }, [canCreate]);

  if (!canCreate) {
    return null;
  }

  const handleSubmit = values => {
    setSaving(true);
    Community.create(values)
      .then(post => {
        notification.success("Post created.");
        navigateTo(`community/${post.id}`);
      })
      .catch(() => notification.error("Failed to create post."))
      .finally(() => setSaving(false));
  };

  return (
    <div className="page-create-form community-page">
      <div className="container">
      <CreatePageLayout backHref="community" backLabel="Back to Community" />
      <div className="community-layout">
        <div className="create-page-form__body">
          <Form
            form={form}
            layout="vertical"
            initialValues={{ category: "general" }}
            onFinish={handleSubmit}
          >
            <Form.Item name="title" label="Title" rules={[{ required: true, message: "Title is required" }]}>
              <Input maxLength={255} placeholder="What would you like to discuss?" />
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
              <TextArea rows={12} placeholder="Share your question, tip, or dashboard idea..." />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={saving} className="m-r-10">
                Publish
              </Button>
              <Link.Button href="community" disabled={saving}>
                Cancel
              </Link.Button>
            </Form.Item>
          </Form>
        </div>
      </div>
      </div>
    </div>
  );
}

routes.register(
  "Community.New",
  routeWithUserSession({
    path: "/community/new",
    title: "New community post",
    render: pageProps => <CommunityNewPage {...pageProps} />,
  })
);

export default CommunityNewPage;
