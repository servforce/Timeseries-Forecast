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
          description="先 Zero-shot 跑基线；若效果不理想，且用户可提供强相关协变量，可以使用 Finetune。需要评估指标（WQL/WAPE）时，在 Markdown JSON 中提供 test_data。"
        />

        <Title level={5}>1. 输入文件（Markdown）</Title>
        <Paragraph>
          上传 <Text code>.md</Text> 文件，将待预测数据按格式要求整理为一个 <Text code>```json</Text>{" "}
          代码块。
        </Paragraph>
        <Paragraph>
          上传格式要求：必要三列：时间（列名定义为timestamp）、ID（为每条序列定义一个任意id，列名为item_id）、目标列（待预测目标，列名定义为target）。
          可以按需上传协变量，并需要传入freq（时间间隔，如日频数据用D，时频数据用H）。详细格式参见输入样例。
        </Paragraph>
        <Divider />

        <Title level={5}>2. 参数说明</Title>
        <Paragraph>
          <Text strong>Prediction Length</Text>：预测步长（未来预测点数）。
        </Paragraph>
        <Paragraph>
          <Text strong>Quantiles</Text>：分位数输出（0.05~0.95，步长 0.05）。
        </Paragraph>
        <Paragraph>
          <Text strong>Metrics</Text>：评估指标选择（WQL/WAPE/IC/IR），可多选。
        </Paragraph>
        <Paragraph>
          <Text strong>Context Length</Text>：模型预测的上下文长度（默认 512）。模型根据上下文长度，学习context_length长度的历史序列规律，用户根据序列长度按需调整。
        </Paragraph>
        <Paragraph>
          <Text strong>With Covariates</Text>：开启后需要在 Markdown JSON 中提供 <Text code>future_cov</Text> 与{" "}。提供协变量长度需要包含未来预测步长区间的数据。
          还需要提供与协变量列名一一对应的<Text code>known_covariates_names</Text>列。关闭后即使提供协变量模型也不会使用。
        </Paragraph>
        <Paragraph>
          <Text strong>Finetune 参数</Text>：Steps/LR/BatchSize 控制微调强度与耗时，建议从小步数开始。
        </Paragraph>

        <Divider />

        <Title level={5}>3. 评估指标（WQL / WAPE / IC / IR）</Title>
        <Paragraph>
          目前支持四个指标的输出：WQL、WAPE、IC、IR
        </Paragraph>
        <Paragraph>
          
        </Paragraph>
        <Paragraph>
        </Paragraph>

        <Divider />

        <Title level={5}>4. 可视化窗口</Title>
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
