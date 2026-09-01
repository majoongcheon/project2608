export interface TreeNode {
  feature: number[]; threshold: number[]; left: number[]; right: number[]; value: number[][];
}
export interface ModelPayload {
  model_version: string;
  question_set_version: string;
  family: 'logit' | 'rf' | 'et';
  features: string[];
  classes: number[];
  decision_weights?: number[];
  missing_sentinel: number;
  // logit
  categories?: number[][];
  spans?: number[][];
  coef?: number[][];
  intercept?: number[];
  expected_contrib?: number[][];
  // tree
  trees?: TreeNode[];
}
export interface Uncertainty {
  tau_conf: number;
  tau_dens: number;
  freq_table: Record<string, Record<string, number>>;
}
