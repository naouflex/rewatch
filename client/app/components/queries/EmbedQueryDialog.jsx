import { uniqueId } from "lodash";
import React from "react";
import PropTypes from "prop-types";
import Alert from "antd/lib/alert";
import Checkbox from "antd/lib/checkbox";
import Form from "antd/lib/form";
import InputNumber from "antd/lib/input-number";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell, ModalSection } from "@/components/ModalShell";
import { clientConfig } from "@/services/auth";
import CodeBlock from "@/components/CodeBlock";

import "./EmbedQueryDialog.less";

class EmbedQueryDialog extends React.Component {
  static propTypes = {
    dialog: DialogPropType.isRequired,
    query: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    visualization: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  };

  state = {
    enableChangeIframeSize: false,
    iframeWidth: 720,
    iframeHeight: 391,
  };

  constructor(props) {
    super(props);
    const { query, visualization } = props;
    this.embedUrl = `${clientConfig.basePath}embed/query/${query.id}/visualization/${visualization.id}?api_key=${
      query.api_key
    }&${query.getParameters().toUrlParams()}`;

    if (window.snapshotUrlBuilder) {
      this.snapshotUrl = window.snapshotUrlBuilder(query, visualization);
    }
  }

  urlEmbedLabelId = uniqueId("url-embed-label");
  iframeEmbedLabelId = uniqueId("iframe-embed-label");

  render() {
    const { query, dialog } = this.props;
    const { enableChangeIframeSize, iframeWidth, iframeHeight } = this.state;

    return (
      <ModalShell
        dialog={dialog}
        title="Embed Query"
        description="Share this visualization with a public URL or iframe embed code."
        size="lg"
        footer="close"
        className="embed-query-dialog">
        {query.is_safe ? (
          <>
            <ModalSection title="Public URL">
              <CodeBlock aria-labelledby={this.urlEmbedLabelId} data-test="EmbedIframe" copyable>
                {this.embedUrl}
              </CodeBlock>
            </ModalSection>
            <ModalSection title="IFrame embed">
              <CodeBlock aria-labelledby={this.iframeEmbedLabelId} copyable>
                {`<iframe src="${this.embedUrl}" width="${iframeWidth}" height="${iframeHeight}"></iframe>`}
              </CodeBlock>
              <Form className="m-t-10" layout="inline">
                <Form.Item>
                  <Checkbox
                    checked={enableChangeIframeSize}
                    onChange={e => this.setState({ enableChangeIframeSize: e.target.checked })}
                  />
                </Form.Item>
                <Form.Item label="Width">
                  <InputNumber
                    className="size-input"
                    value={iframeWidth}
                    onChange={value => this.setState({ iframeWidth: value })}
                    size="small"
                    disabled={!enableChangeIframeSize}
                  />
                </Form.Item>
                <Form.Item label="Height">
                  <InputNumber
                    className="size-input"
                    value={iframeHeight}
                    onChange={value => this.setState({ iframeHeight: value })}
                    size="small"
                    disabled={!enableChangeIframeSize}
                  />
                </Form.Item>
              </Form>
            </ModalSection>
            {this.snapshotUrl && (
              <ModalSection title="Image embed">
                <CodeBlock copyable>{this.snapshotUrl}</CodeBlock>
              </ModalSection>
            )}
          </>
        ) : (
          <Alert
            message="Currently it is not possible to embed queries that contain text parameters."
            type="error"
            data-test="EmbedErrorAlert"
          />
        )}
      </ModalShell>
    );
  }
}

export default wrapDialog(EmbedQueryDialog);
