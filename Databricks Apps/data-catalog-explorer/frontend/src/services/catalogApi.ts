import type { Catalog, Schema, DataObject, LineageEdge, GlossaryTerm, FilterOptions } from '../types';
import { catalogs, schemas, dataObjects, lineageEdges, glossaryTerms } from '../data/catalog';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const LATENCY = 50;

function matchesFilters(obj: DataObject, filters?: FilterOptions): boolean {
  if (!filters) return true;
  if (filters.domain?.length && !filters.domain.includes(obj.domain)) return false;
  if (filters.owner?.length && !filters.owner.includes(obj.owner)) return false;
  if (filters.sensitivity?.length && !filters.sensitivity.includes(obj.sensitivity)) return false;
  if (filters.type?.length && !filters.type.includes(obj.type)) return false;
  if (filters.status?.length && !filters.status.includes(obj.status)) return false;
  if (filters.tags?.length && !filters.tags.some(t => obj.tags.includes(t))) return false;
  if (filters.search) {
    const q = filters.search.toLowerCase();
    const searchable = [
      obj.name, obj.friendlyName, obj.description, obj.businessDescription,
      obj.owner, obj.domain, ...obj.tags,
    ].join(' ').toLowerCase();
    if (!searchable.includes(q)) return false;
  }
  return true;
}

export const catalogApi = {
  async listCatalogs(): Promise<Catalog[]> {
    await delay(LATENCY);
    return [...catalogs];
  },

  async listSchemas(catalogId: string): Promise<Schema[]> {
    await delay(LATENCY);
    return schemas.filter(s => s.catalogId === catalogId);
  },

  async listObjects(schemaId: string, filters?: FilterOptions): Promise<DataObject[]> {
    await delay(LATENCY);
    return dataObjects.filter(o => o.schemaId === schemaId && matchesFilters(o, filters));
  },

  async getObjectDetails(objectId: string): Promise<DataObject | null> {
    await delay(LATENCY);
    return dataObjects.find(o => o.id === objectId) ?? null;
  },

  async search(query: string, filters?: FilterOptions): Promise<DataObject[]> {
    await delay(LATENCY);
    const q = query.toLowerCase();
    return dataObjects.filter(o => {
      const searchable = [
        o.name, o.friendlyName, o.description, o.businessDescription,
        o.owner, o.domain, o.steward, ...o.tags,
        ...o.columns.map(c => c.name + ' ' + c.description),
      ].join(' ').toLowerCase();
      return searchable.includes(q) && matchesFilters(o, filters);
    });
  },

  async getGlossary(): Promise<GlossaryTerm[]> {
    await delay(LATENCY);
    return [...glossaryTerms].sort((a, b) => a.term.localeCompare(b.term));
  },

  async getLineage(objectId: string): Promise<{ upstream: LineageEdge[]; downstream: LineageEdge[] }> {
    await delay(LATENCY);
    return {
      upstream: lineageEdges.filter(e => e.toTableId === objectId),
      downstream: lineageEdges.filter(e => e.fromTableId === objectId),
    };
  },

  async getPopular(): Promise<DataObject[]> {
    await delay(LATENCY);
    return [...dataObjects].sort((a, b) => b.popularityScore - a.popularityScore).slice(0, 6);
  },

  async getRecent(): Promise<DataObject[]> {
    await delay(LATENCY);
    return [...dataObjects]
      .filter(o => o.status === 'ACTIVE')
      .sort((a, b) => new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime())
      .slice(0, 6);
  },

  async getAllObjects(filters?: FilterOptions): Promise<DataObject[]> {
    await delay(LATENCY);
    return dataObjects.filter(o => matchesFilters(o, filters));
  },

  getObjectById(id: string): DataObject | undefined {
    return dataObjects.find(o => o.id === id);
  },

  getSchemaById(id: string): Schema | undefined {
    return schemas.find(s => s.id === id);
  },

  getCatalogById(id: string): Catalog | undefined {
    return catalogs.find(c => c.id === id);
  },

  getAllOwners(): string[] {
    return [...new Set(dataObjects.map(o => o.owner))].sort();
  },

  getAllTags(): string[] {
    return [...new Set(dataObjects.flatMap(o => o.tags))].sort();
  },
};
