import momentGenerateConfig from "@rc-component/picker/lib/generate/moment";
import generatePicker from "antd/lib/date-picker/generatePicker";

const MomentPicker = generatePicker(momentGenerateConfig);

export const DatePicker = MomentPicker;
export const WeekPicker = MomentPicker.WeekPicker;
export const MonthPicker = MomentPicker.MonthPicker;
export const YearPicker = MomentPicker.YearPicker;
export const TimePicker = MomentPicker.TimePicker;
export const QuarterPicker = MomentPicker.QuarterPicker;
export const RangePicker = MomentPicker.RangePicker;

export default MomentPicker;
