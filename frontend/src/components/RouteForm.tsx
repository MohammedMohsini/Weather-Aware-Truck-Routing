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
  loading: boolean;
};

export function RouteForm({ values, onChange, onSubmit, loading }: RouteFormProps) {
  const localDate = values.departure_time || new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16);

  return (
    <form
      className="route-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="field-group">
        <label htmlFor="origin">Origin</label>
        <input
          id="origin"
          value={values.origin}
          onChange={(event) => onChange('origin', event.target.value)}
          placeholder="New York, NY"
        />
      </div>

      <div className="field-group">
        <label htmlFor="destination">Destination</label>
        <input
          id="destination"
          value={values.destination}
          onChange={(event) => onChange('destination', event.target.value)}
          placeholder="Chicago, IL"
        />
      </div>

      <div className="field-group">
        <label htmlFor="departure_time">Departure</label>
        <input
          id="departure_time"
          type="datetime-local"
          value={localDate}
          onChange={(event) => onChange('departure_time', event.target.value)}
        />
      </div>

      <div className="field-group">
        <label htmlFor="load_lb">Load weight (lb)</label>
        <input
          id="load_lb"
          type="number"
          min="1"
          value={values.load_lb}
          onChange={(event) => onChange('load_lb', Number(event.target.value) || 0)}
        />
      </div>

      <div className="field-group">
        <label htmlFor="interval_miles">Checkpoint interval</label>
        <select
          id="interval_miles"
          value={values.interval_miles}
          onChange={(event) => onChange('interval_miles', Number(event.target.value))}
        >
          <option value={10}>10 miles</option>
          <option value={25}>25 miles</option>
          <option value={50}>50 miles</option>
        </select>
      </div>

      <button type="submit" className="primary-button" disabled={loading}>
        {loading ? 'Analyzing…' : 'Analyze routes'}
      </button>
    </form>
  );
}
