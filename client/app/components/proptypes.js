import PropTypes from "prop-types";
import { wrap } from "lodash";
import moment from "moment";

export const DataSource = PropTypes.shape({
  syntax: PropTypes.string,
  options: PropTypes.shape({
    doc: PropTypes.string,
    doc_url: PropTypes.string,
  }),
  type_name: PropTypes.string,
});

export const Table = PropTypes.shape({
  columns: PropTypes.arrayOf(PropTypes.string).isRequired,
});

export const Schema = PropTypes.arrayOf(Table);

export const RefreshScheduleType = PropTypes.shape({
  interval: PropTypes.number,
  time: PropTypes.string,
  day_of_week: PropTypes.string,
  until: PropTypes.string,
});

export const RefreshScheduleDefault = {
  interval: null,
  time: null,
  day_of_week: null,
  until: null,
};

export const UserProfile = PropTypes.shape({
  id: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  email: PropTypes.string.isRequired,
  profileImageUrl: PropTypes.string,
  apiKey: PropTypes.string,
  isDisabled: PropTypes.bool,
});

export const Destination = PropTypes.shape({
  id: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  icon: PropTypes.string.isRequired,
  type: PropTypes.string.isRequired,
});

export const Query = PropTypes.shape({
  id: PropTypes.any.isRequired,
  name: PropTypes.string.isRequired,
  description: PropTypes.string,
  data_source_id: PropTypes.any.isRequired,
  created_at: PropTypes.string.isRequired,
  updated_at: PropTypes.string,
  user: UserProfile,
  query: PropTypes.string,
  queryHash: PropTypes.string,
  is_safe: PropTypes.bool.isRequired,
  is_draft: PropTypes.bool.isRequired,
  is_archived: PropTypes.bool.isRequired,
  api_key: PropTypes.string.isRequired,
});

export const AlertOptions = PropTypes.shape({
  column: PropTypes.string,
  selector: PropTypes.oneOf(["first", "min", "max"]),
  op: PropTypes.oneOf([">", ">=", "<", "<=", "==", "!="]),
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  custom_subject: PropTypes.string,
  custom_body: PropTypes.string,
});

export const Alert = PropTypes.shape({
  id: PropTypes.any,
  name: PropTypes.string,
  created_at: PropTypes.string,
  last_triggered_at: PropTypes.string,
  updated_at: PropTypes.string,
  rearm: PropTypes.number,
  state: PropTypes.oneOf(["ok", "triggered", "unknown"]),
  user: UserProfile,
  query: Query,
  options: PropTypes.shape({
    column: PropTypes.string,
    selector: PropTypes.string,
    op: PropTypes.string,
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  }).isRequired,
});

export const ModelOptions = PropTypes.shape({
  op_train: PropTypes.string,
  op_predict: PropTypes.string,
  column_train: PropTypes.string,
  column_predict: PropTypes.string,
  value_train: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  value_predict: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  regressor: PropTypes.string,
  train_size: PropTypes.number,
  test_size: PropTypes.number,
  random_state: PropTypes.number,
  features: PropTypes.arrayOf(PropTypes.string),
  targets: PropTypes.arrayOf(PropTypes.string),
  categories: PropTypes.arrayOf(PropTypes.string),
  rearm_train: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  rearm_predict: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
});

export const MLModel = PropTypes.shape({
  id: PropTypes.any,
  name: PropTypes.string,
  description: PropTypes.string,
  created_at: PropTypes.string,
  updated_at: PropTypes.string,
  state: PropTypes.string,
  state_train: PropTypes.string,
  state_predict: PropTypes.string,
  user: UserProfile,
  query: Query,
  options: ModelOptions,
  tags: PropTypes.arrayOf(PropTypes.string),
});

export const PredictionResult = PropTypes.shape({
  id: PropTypes.any,
  model_id: PropTypes.any,
  query_id: PropTypes.any,
  user: UserProfile,
  query: Query,
  model: MLModel,
  content: PropTypes.string,
  created_at: PropTypes.string,
  tags: PropTypes.arrayOf(PropTypes.string),
});

function checkMoment(isRequired, props, propName, componentName) {
  const value = props[propName];
  const isRequiredValid = isRequired && value !== null && value !== undefined && moment.isMoment(value);
  const isOptionalValid = !isRequired && (value === null || value === undefined || moment.isMoment(value));
  if (!isRequiredValid && !isOptionalValid) {
    return new Error("Prop `" + propName + "` supplied to `" + componentName + "` should be a Moment.js instance.");
  }
}

export const Moment = wrap(false, checkMoment);
Moment.isRequired = wrap(true, checkMoment);
