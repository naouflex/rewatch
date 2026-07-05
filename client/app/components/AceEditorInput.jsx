import React, { forwardRef } from "react";
import AceEditor from "react-ace";
import "ace-builds/src-noconflict/theme-textmate";
import "ace-builds/src-noconflict/theme-tomorrow_night";

import { useTheme } from "@/components/ThemeProvider";
import "./AceEditorInput.less";

function AceEditorInput(props, ref) {
  const { isDarkMode } = useTheme();
  const { theme = isDarkMode ? "tomorrow_night" : "textmate", ...rest } = props;

  return (
    <div className="ace-editor-input" data-test={props["data-test"]}>
      <AceEditor
        ref={ref}
        mode="sql"
        theme={theme}
        height="100px"
        editorProps={{ $blockScrolling: Infinity }}
        showPrintMargin={false}
        {...rest}
      />
    </div>
  );
}

export default forwardRef(AceEditorInput);
