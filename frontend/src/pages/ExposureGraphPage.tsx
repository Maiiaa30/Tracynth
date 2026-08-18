import { useEffect, useRef, useState } from 'react';
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Section } from '../components/Page';
import { EmptyState, ErrorState, LoadingState } from '../components/AsyncState';
import { apiRequest, asPage } from '../lib/api';
import { text } from '../lib/format';
import type { GraphEntity, GraphRelationship, Page } from '../types/api';

function endpointId(value: GraphRelationship['source']): string | undefined {
  if (typeof value === 'string') return value;
  return value && typeof value.id === 'string' ? value.id : undefined;
}

export function ExposureGraphPage() {
  const container = useRef<HTMLDivElement>(null);
  const graph = useRef<Core | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['exposure-graph'],
    queryFn: async () => {
      const [entityResult, relationshipResult] = await Promise.all([
        apiRequest<Page<GraphEntity> | GraphEntity[]>('/entities/?page_size=250'),
        apiRequest<Page<GraphRelationship> | GraphRelationship[]>('/relationships/?page_size=500'),
      ]);
      return { entities: asPage(entityResult), relationships: asPage(relationshipResult) };
    },
  });

  useEffect(() => {
    if (!container.current || !query.data?.entities.results.length) return;
    const nodeIds = new Set(query.data.entities.results.map((entity) => entity.id));
    const elements: ElementDefinition[] = query.data.entities.results.map((entity) => ({
      data: {
        id: entity.id,
        label: text(entity.display_value ?? entity.value, entity.id.slice(0, 8)),
        type: text(entity.entity_type ?? entity.type, 'entity'),
      },
    }));
    for (const relationship of query.data.relationships.results) {
      const source = endpointId(relationship.source);
      const target = endpointId(relationship.target);
      if (source && target && nodeIds.has(source) && nodeIds.has(target)) {
        elements.push({
          data: {
            id: relationship.id,
            source,
            target,
            label: text(relationship.relationship_type ?? relationship.type, ''),
          },
        });
      }
    }
    graph.current?.destroy();
    const instance = cytoscape({
      container: container.current,
      elements,
      layout: { name: 'cose', animate: false, padding: 32 },
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#796bea',
            label: 'data(label)',
            color: '#e8eaf6',
            'font-size': 10,
            'text-valign': 'bottom',
            'text-margin-y': 8,
            width: 18,
            height: 18,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1,
            'line-color': '#454c70',
            'target-arrow-color': '#454c70',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
          },
        },
        {
          selector: ':selected',
          style: {
            'background-color': '#58b4ff',
            'line-color': '#58b4ff',
            'target-arrow-color': '#58b4ff',
          },
        },
      ],
    });
    instance.on('select', 'node', () => {
      const selection = instance.$('node:selected').first();
      setSelected(selection.empty() ? null : selection.id());
    });
    graph.current = instance;
    return () => {
      instance.destroy();
      graph.current = null;
    };
  }, [query.data]);

  const selectedEntity = query.data?.entities.results.find((entity) => entity.id === selected);
  return (
    <>
      <PageHeader
        title="Exposure graph"
        description="Evidence-backed entities and relationships returned by the bounded graph API."
      />
      <Section
        title="Relationship map"
        description="Drag to pan, scroll to zoom, and select a node for details."
        className="graph-panel"
      >
        {query.isPending ? <LoadingState label="Loading graph" /> : null}
        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : null}
        {query.data && !query.data.entities.results.length ? (
          <EmptyState
            title="No graph data"
            detail="Entities will appear after collectors produce normalized evidence."
          />
        ) : null}
        {query.data?.entities.results.length ? (
          <div className="graph-layout">
            <div
              ref={container}
              className="graph-canvas"
              role="img"
              aria-label={`Exposure graph with ${query.data.entities.count} entities`}
            />
            <aside className="graph-detail" aria-live="polite">
              <h3>
                {selectedEntity
                  ? text(selectedEntity.display_value ?? selectedEntity.value)
                  : 'Select a node'}
              </h3>
              {selectedEntity ? (
                <dl>
                  <dt>Type</dt>
                  <dd>{text(selectedEntity.entity_type ?? selectedEntity.type)}</dd>
                  <dt>State</dt>
                  <dd>{text(selectedEntity.state)}</dd>
                  <dt>Identifier</dt>
                  <dd className="mono">{selectedEntity.id}</dd>
                </dl>
              ) : (
                <p>Node details are shown here without exposing normalized values unnecessarily.</p>
              )}
            </aside>
          </div>
        ) : null}
      </Section>
    </>
  );
}
