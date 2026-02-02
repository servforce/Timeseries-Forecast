import { Alert, Divider, Drawer, Space, Typography } from "antd";

const { Paragraph, Text, Title } = Typography;

export default function TutorialDrawer(props: { open: boolean; onClose: () => void }) {
  return (
    <Drawer
      title="使用教程"
      placement="right"
      onClose={props.onClose}
      open={props.open}
      width={560}
    >
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Alert
          type="info"
          showIcon
          message="推荐工作流"
          description="先 Zero-shot 跑基线；若效果不理想，且用户可提供强相关协变量，可以使用 Finetune接口进行模型微调并预测。"
        />

        <Title level={5}>1. 输入文件（Markdown）</Title>
        <Paragraph>
          上传 <Text code>.md</Text> 文件，将待预测数据按格式要求整理为一个 <Text code>```json</Text>{" "}
          代码块。
        </Paragraph>
        <Paragraph>
          上传格式要求：必要三列：时间（列名定义为 <Text code>timestamp</Text>）、ID（为每条序列定义一个任意id，列名为 <Text code>item_id</Text>）、目标列（待预测目标，列名定义为 <Text code>target</Text>）。
          可以按需上传协变量，并需要传入freq（时间间隔，如日频数据用D，时频数据用H）。详细格式参见输入样例。
        </Paragraph>
        <Paragraph>
          协变量支持：输入数据传入 <Text code>covariates</Text> 列作为未来协变量传入。传入 <Text code>known_covariates_names</Text>{" "}
          定义未来已知协变量（需要提供未来预测步长天数的协变量数据），其余协变量将被作为历史协变量使用。
        </Paragraph>
        <Paragraph>
          分类协变量支持：传入 <Text code>category_cov_name</Text> 指定分类协变量列名，例如是否促销（0/1）、星期几等可作为分类协变量；
          未在 <Text code>category_cov_name</Text> 中的协变量默认按数值型处理，例如物价、气温等连续值。
          注：合理传入协变量类型，有助于提升模型效果。
        </Paragraph>
        <Divider />

        <Title level={5}>2. 参数说明</Title>
        <Paragraph>
          <Text strong>Prediction Length</Text>：预测步长（未来预测点数）。
        </Paragraph>
        <Paragraph>
          <Text strong>Quantiles</Text>：分位数输出（支持0.05~0.95，步长 0.05）。
        </Paragraph>
        <Paragraph>
          <Text strong>Metrics</Text>：评估指标选择（支持WQL/WAPE/IC/IR输出），可多选。
        </Paragraph>
        <Paragraph>
          <Text strong>Context Length</Text>：模型预测的可学习上下文长度（默认 512，最大支持8192）。模型根据上下文长度，学习context_length长度的历史序列规律。用户根据序列覆盖长度及频率调整。
        </Paragraph>
        <Paragraph>
          <Text strong>With Covariates</Text>：开启后需要在 Markdown JSON 中提供 <Text code>covariates</Text>{" "}
          与 <Text code>known_covariates_names</Text>。提供协变量长度需要包含未来预测步长区间的数据。根据提供的{" "}
          <Text code>known_covariates_names</Text> 列作为未来已知协变量，其余未在{" "}
          <Text code>known_covariates_names</Text> 中的协变量将被作为仅历史协变量。<Text strong>With Covariates</Text>{" "}
          关闭后即使提供协变量模型也会进行单变量预测。
        </Paragraph>
        <Paragraph>
          <Text strong>Finetune 参数</Text>：Steps/LR/BatchSize 一些微调的参数，控制微调性能，微调建议序列数大于100条，且历史长度大于512。
        </Paragraph>

        <Divider />

        <Title level={5}>3. 接口使用说明（Zero-shot / Finetune）</Title>
        <Paragraph>
          <Text strong>Zero-shot</Text>：上传 Markdown 后直接预测，不保存模型，也不会返回 <Text code>model_id</Text>。
        </Paragraph>
        <Paragraph>
          <Text strong>Finetune</Text>：上传数据后先微调再预测。若开启 <Text code>save_model</Text>，会返回 <Text code>model_id</Text>，后续可直接传入该
          <Text code>model_id</Text> 复用预测（跳过再次微调）。
        </Paragraph>
        <Paragraph>
          <Text strong>模型保留策略</Text>：已保存的微调模型默认保留 14 天，超过期限会自动清理，需要重新微调生成新的 <Text code>model_id</Text>。
        </Paragraph>

        <Divider />

        <Title level={5}>4. 评估指标（WQL / WAPE / IC / IR）</Title>
        <Paragraph>
          目前支持四个指标的输出：WQL、WAPE、IC、IR
        </Paragraph>
        <Paragraph>
          <Text strong>WQL</Text>：加权量化损失，衡量预测值与真实值之间的差距，越小越好。
        </Paragraph>
        <Paragraph>
          <Text strong>WAPE</Text>：加权绝对百分比误差，衡量预测值与真实值之间的相对差距，越小越好。
        </Paragraph>
        <Paragraph>
          <Text strong>IC</Text>：信息量准则，衡量模型对未来信息的利用程度，越大越好。
        </Paragraph>
        <Paragraph>
          <Text strong>IR</Text>：信息比率，衡量模型预测值与真实值之间的相关性，越大越好。
        </Paragraph>
        <Divider />

        <Title level={5}>5. 可视化窗口</Title>
        <Paragraph>
        可视化展示：阴影区域表示p10-p90置信区间,主线表示p50。
        </Paragraph>
        <Paragraph>
          图表主线展示 <Text strong>P50</Text>，并用阴影区域展示 <Text strong>P10~P90</Text> 置信区间。
        </Paragraph>
      </Space>
    </Drawer>
  );
}
