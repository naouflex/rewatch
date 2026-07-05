import React from "react";
import sanitize from "@/services/sanitize";

type Props = {
  children?: string;
  [key: string]: any;
};

const HtmlContent = React.memo(function HtmlContent({ children = "", ...props }: Props) {
  return (
    <div
      {...props}
      dangerouslySetInnerHTML={{ __html: sanitize(children) }} // eslint-disable-line react/no-danger
    />
  );
});

export default HtmlContent;
