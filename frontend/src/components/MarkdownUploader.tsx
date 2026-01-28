import { InboxOutlined } from "@ant-design/icons";
import { Alert, Space, Typography, Upload } from "antd";
import type { UploadProps } from "antd";
import { useMemo, useState } from "react";
import { precheckMarkdownHasJsonFence, readFileText } from "../utils/markdown";

const { Dragger } = Upload;
const { Text } = Typography;

export type MarkdownFileState = {
  file: File;
  text?: string;
  precheckOk: boolean;
  precheckMessage?: string;
};

export default function MarkdownUploader(props: {
  value: MarkdownFileState | null;
  onChange: (v: MarkdownFileState | null) => void;
}) {
  const [loadingText, setLoadingText] = useState(false);

  const uploadProps: UploadProps = useMemo(
    () => ({
      multiple: false,
      maxCount: 1,
      beforeUpload: async (file) => {
        if (!file.name.toLowerCase().endsWith(".md")) {
          props.onChange({
            file: file as File,
            precheckOk: false,
            precheckMessage: "仅支持上传 .md 文件",
          });
          return Upload.LIST_IGNORE;
        }

        const precheck = await precheckMarkdownHasJsonFence(file as File);
        props.onChange({
          file: file as File,
          precheckOk: precheck.ok,
          precheckMessage: precheck.message,
        });

        // 只在预检通过时读取完整文本（避免大文件无意义读取）
        if (precheck.ok) {
          setLoadingText(true);
          try {
            const text = await readFileText(file as File);
            props.onChange({
              file: file as File,
              precheckOk: precheck.ok,
              precheckMessage: precheck.message,
              text,
            });
          } finally {
            setLoadingText(false);
          }
        }
        return false;
      },
      onRemove: () => props.onChange(null),
      showUploadList: false,
    }),
    [props],
  );

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Dragger {...uploadProps} disabled={loadingText}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">拖拽或点击上传 Markdown</p>
        <p className="ant-upload-hint">仅限 .md，建议包含一个 ```json 代码块</p>
      </Dragger>

      {props.value?.file && (
        <div>
          <Text>
            文件：{props.value.file.name}（{Math.ceil(props.value.file.size / 1024)} KB）
          </Text>
        </div>
      )}

      {props.value?.precheckMessage && (
        <Alert
          type={props.value.precheckOk ? "success" : "warning"}
          showIcon
          message={props.value.precheckMessage}
        />
      )}
    </Space>
  );
}

