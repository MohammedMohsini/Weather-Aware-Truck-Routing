import { useEffect, useId, useRef, useState } from 'react';

import { geocodePlaces, type PlaceResult } from '../api/client';

type RouteFormValues = {
  origin: string;
  destination: string;
  departure_time: string;
  load_lb: number;
  interval_miles: number;
};

type RouteFormProps = {
  values: RouteFormValues;
  onChange: (field: keyof RouteFormValues, value: string | number) => void;
  onSubmit: () => void;
  onExample: () => void;
  loading: boolean;
  progressMessage: string;
};

function PlaceAutocomplete({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const listboxId = useId();
  const [results, setResults] = useState<PlaceResult[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [searchComplete, setSearchComplete] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [resultQuery, setResultQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const selectedResult = useRef(false);

  useEffect(() => {
    const query = value.trim();
    if (!focused) {
      return;
    }
    if (selectedResult.current) {
      selectedResult.current = false;
      return;
    }
    if (query.length < 2) {
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      setSearchError('');
      void geocodePlaces(query, controller.signal)
        .then((places) => {
          setResults(places);
          setResultQuery(query);
          setActiveIndex(-1);
          setSearchComplete(true);
        })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) {
            setResults([]);
            setResultQuery(query);
            setSearchComplete(true);
            setSearchError(
              error instanceof Error
                ? `Geocoding failed: ${error.message}`
                : 'Geocoding failed. Please try again.',
            );
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });
    }, 300);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [focused, value]);

  const selectResult = (place: PlaceResult) => {
    selectedResult.current = true;
    onChange(place.display_name);
    setResults([]);
    setSearchComplete(false);
    setSearchError('');
  };
  const visibleResults = focused && resultQuery === value.trim() ? results : [];
  const visibleSearchError = focused && resultQuery === value.trim() ? searchError : '';
  const showNoResults = focused && resultQuery === value.trim() && searchComplete && !results.length;

  return (
    <div className="field-group">
      <label htmlFor={id}>{label}</label>
      <div className="autocomplete-wrap">
        <input
          id={id}
          required
          autoComplete="off"
          value={value}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={visibleResults.length > 0}
          aria-controls={listboxId}
          aria-activedescendant={activeIndex >= 0 ? `${listboxId}-${activeIndex}` : undefined}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onChange={(event) => {
            setLoading(false);
            setResults([]);
            setSearchComplete(false);
            setSearchError('');
            onChange(event.target.value);
          }}
          onKeyDown={(event) => {
            if (!visibleResults.length) {
              return;
            }
            if (event.key === 'ArrowDown') {
              event.preventDefault();
              setActiveIndex((index) => (index + 1) % visibleResults.length);
            } else if (event.key === 'ArrowUp') {
              event.preventDefault();
              setActiveIndex((index) => (index <= 0 ? visibleResults.length - 1 : index - 1));
            } else if (event.key === 'Enter' && activeIndex >= 0) {
              event.preventDefault();
              selectResult(visibleResults[activeIndex]);
            } else if (event.key === 'Escape') {
              setResults([]);
            }
          }}
        />
        {loading ? (
          <span className="suggestion-status" role="status">
            Searching…
          </span>
        ) : null}
        {visibleResults.length > 0 ? (
          <ul id={listboxId} className="suggestion-list" role="listbox" aria-label={`${label} suggestions`}>
            {visibleResults.map((place, index) => (
              <li key={`${place.latitude}-${place.longitude}-${place.display_name}`} role="presentation">
                <button
                  id={`${listboxId}-${index}`}
                  type="button"
                  role="option"
                  aria-selected={index === activeIndex}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectResult(place)}
                >
                  {place.display_name}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        {!loading && showNoResults ? <span className="suggestion-status">No results</span> : null}
      </div>
      {visibleSearchError ? (
        <p className="field-error" role="alert">
          {visibleSearchError}
        </p>
      ) : null}
    </div>
  );
}

export function RouteForm({
  values,
  onChange,
  onSubmit,
  onExample,
  loading,
  progressMessage,
}: RouteFormProps) {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [loadError, setLoadError] = useState('');

  return (
    <form
      className="route-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (!Number.isFinite(values.load_lb) || values.load_lb <= 0) {
          setLoadError('Enter a load weight greater than 0 lb.');
          return;
        }
        setLoadError('');
        onSubmit();
      }}
    >
      <PlaceAutocomplete
        id="origin"
        label="Origin"
        value={values.origin}
        onChange={(value) => onChange('origin', value)}
      />
      <PlaceAutocomplete
        id="destination"
        label="Destination"
        value={values.destination}
        onChange={(value) => onChange('destination', value)}
      />

      <div className="field-group">
        <label htmlFor="departure_time">Departure · {timezone}</label>
        <input
          id="departure_time"
          type="datetime-local"
          required
          value={values.departure_time}
          onChange={(event) => onChange('departure_time', event.target.value)}
        />
        <p className="field-hint">Displayed in your local timezone.</p>
      </div>

      <div className="field-group">
        <label htmlFor="load_lb">Load weight</label>
        <div className="weight-input-wrap">
          <input
            id="load_lb"
            type="number"
            min="1"
            step="1"
            required
            value={values.load_lb || ''}
            aria-invalid={Boolean(loadError)}
            aria-describedby={loadError ? 'load-error' : undefined}
            onChange={(event) => {
              onChange('load_lb', Number(event.target.value) || 0);
              setLoadError('');
            }}
          />
          <span>lb</span>
        </div>
        {loadError ? (
          <p id="load-error" className="field-error" role="alert">
            {loadError}
          </p>
        ) : null}
      </div>

      <fieldset className="interval-fieldset">
        <legend>Checkpoint interval</legend>
        <div className="segmented-control" role="group" aria-label="Checkpoint interval in miles">
          {[10, 25, 50].map((interval) => (
            <button
              key={interval}
              type="button"
              aria-pressed={values.interval_miles === interval}
              onClick={() => onChange('interval_miles', interval)}
            >
              {interval} mi
            </button>
          ))}
        </div>
      </fieldset>

      <div className="form-actions">
        <button type="submit" className="primary-button" disabled={loading}>
          {loading ? progressMessage || 'Analyzing…' : 'Analyze route'}
        </button>
        <button type="button" className="secondary-button" onClick={onExample} disabled={loading}>
          Try an example
        </button>
      </div>
    </form>
  );
}
