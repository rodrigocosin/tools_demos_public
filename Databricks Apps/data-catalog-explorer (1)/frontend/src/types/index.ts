export interface Catalog {
  id: string;
  name: string;
  friendlyName?: string;
  description: string;
  owner: string;
  domain: string;
  tags: string[];
  schemaCount: number;
}

export interface Schema {
  id: string;
  catalogId: string;
  name: string;
  friendlyName?: string;
  description: string;
  owner: string;
  domain: string;
  tags: string[];
  tableCount: number;
}

export type Sensitivity = 'Público' | 'Publico' | 'Interno' | 'Confidencial' | 'PII';
export type ObjectType = 'TABLE' | 'VIEW';
export type ObjectStatus = 'ACTIVE' | 'DEPRECATED';
export type Domain = string;

export interface TableObject {
  id: string;
  schemaId: string;
  catalogId: string;
  name: string;
  friendlyName: string;
  type: ObjectType;
  description: string;
  businessDescription: string;
  usageExamples: string[];
  owner: string;
  steward: string;
  team: string;
  contactChannel: string;
  domain: string;
  tags: string[];
  sensitivity: Sensitivity;
  isPII: boolean;
  pii?: boolean;
  rowCountApprox: number;
  freshness: string;
  lastUpdated: string;
  sla: string;
  updateFrequency?: string;
  status: ObjectStatus;
  deprecationReason?: string;
  popularityScore: number;
  qualityCompleteness: number;
  qualityUniqueness: number;
  qualityConsistency: number;
  qualityScore?: { completeness: number; uniqueness: number; consistency: number };
  governancePolicy?: string;
  retentionDays?: number;
  retention?: string;
  compliance: string[];
  columns: Column[];
}

// Alias for backwards compat
export type DataObject = TableObject;

export interface Column {
  id: string;
  tableId: string;
  name: string;
  friendlyName?: string;
  type: string;
  description: string;
  sensitivity: Sensitivity;
  isPII: boolean;
  pii?: boolean;
  exampleValues: string[];
  nullable?: boolean;
}

export interface Lineage {
  fromTableId: string;
  toTableId: string;
  relationLabel: string;
}

// Alias
export type LineageEdge = Lineage;

export interface GlossaryTerm {
  id?: string;
  term: string;
  definition: string;
  relatedTableIds: string[];
  domain?: string;
  examples?: string[];
}

export interface FilterOptions {
  search?: string;
  domain?: string[];
  owner?: string[];
  sensitivity?: Sensitivity[];
  type?: ObjectType[];
  status?: ObjectStatus[];
  tags?: string[];
}
