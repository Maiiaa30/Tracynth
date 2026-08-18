import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { PageHeader, Section } from '../components/Page';
import { apiRequest, displayError } from '../lib/api';
import type { ApiRecord } from '../types/api';

const moduleOptions = [
  { value: 'dns', label: 'DNS records', detail: 'Resolve and normalize public DNS data.' },
  { value: 'tls', label: 'TLS certificates', detail: 'Inspect public certificate metadata.' },
  { value: 'web', label: 'Web surface', detail: 'Collect bounded HTTP metadata.' },
];

export function NewScanPage() {
  const navigate = useNavigate();
  const [domain, setDomain] = useState('');
  const [modules, setModules] = useState(['dns', 'tls', 'web']);
  const mutation = useMutation({
    mutationFn: async () => {
      const target = await apiRequest<ApiRecord>('/targets/', {
        method: 'POST',
        body: JSON.stringify({
          target_type: 'domain',
          display_value: domain.trim().toLowerCase(),
        }),
      });
      if (typeof target.id !== 'string')
        throw new Error('The target response did not include an ID.');
      const configuration = await apiRequest<ApiRecord>('/scan-configurations/', {
        method: 'POST',
        body: JSON.stringify({
          target: target.id,
          name: `Domain scan · ${domain.trim().toLowerCase()}`,
          enabled_modules: modules,
          collector_settings: {},
        }),
      });
      if (typeof configuration.id !== 'string') {
        throw new Error('The scan configuration response did not include an ID.');
      }
      return apiRequest<ApiRecord>('/scans/', {
        method: 'POST',
        body: JSON.stringify({ target: target.id, configuration: configuration.id }),
      });
    },
    onSuccess: (scan) => {
      if (typeof scan.id !== 'string') throw new Error('The scan response did not include an ID.');
      void navigate(`/scans/${scan.id}`);
    },
  });

  function toggleModule(value: string) {
    setModules((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="New investigation"
        title="Domain scan"
        description="Create a bounded scan against a public domain you are authorized to investigate."
      />
      <Section
        title="Scan scope"
        description="The server revalidates destinations and enforces network budgets."
      >
        <form
          className="stack-form"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <div>
            <label htmlFor="domain">Domain</label>
            <input
              id="domain"
              type="text"
              inputMode="url"
              autoComplete="off"
              placeholder="example.com"
              pattern="^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
              required
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              aria-describedby="domain-help"
            />
            <p id="domain-help" className="field-help">
              Enter a hostname only; paths, credentials, and protocols are not accepted.
            </p>
          </div>
          <fieldset>
            <legend>Collection modules</legend>
            <div className="choice-grid">
              {moduleOptions.map((module) => (
                <label className="choice-card" key={module.value}>
                  <input
                    type="checkbox"
                    checked={modules.includes(module.value)}
                    onChange={() => toggleModule(module.value)}
                  />
                  <span>
                    <strong>{module.label}</strong>
                    <small>{module.detail}</small>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          {mutation.error ? (
            <p className="form-error" role="alert">
              {displayError(mutation.error)}
            </p>
          ) : null}
          <div className="form-actions">
            <button
              className="button"
              type="submit"
              disabled={mutation.isPending || modules.length === 0 || !domain}
            >
              {mutation.isPending ? 'Starting scan…' : 'Start scan'}
            </button>
            <button
              className="button button--secondary"
              type="button"
              onClick={() => void navigate(-1)}
            >
              Cancel
            </button>
          </div>
        </form>
      </Section>
    </>
  );
}
