import { useEffect, useState, type FormEvent } from 'react'
import { AlertTriangle, ArrowDownToLine, Check, LoaderCircle, Plus, Printer, Search, ShoppingCart, Trash2 } from 'lucide-react'
import { apiGet, apiPost, ApiError } from './api'
import pharmacyCareBanner from './assets/pharmacy-care-banner.jpg'
import './operations.css'
import './dashboard.css'

type Drug = { id: number; generic_name: string; brand_name: string; strength: string; dosage_form: string; selling_price: string; prescription_required: boolean; status: string; category: number }
type SaleResult = { id: number; sale_number: string; total_amount: string; payment_method: string; payment_amount: string; completed_at: string }
type CartLine = { drug: Drug; quantity: number }
type CheckoutCustomer = { id: number; full_name: string }
type EligiblePrescription = { id: number; reference: string; remaining: { drug_id: number; drug_name: string; remaining_quantity: number }[] }
type ReportRow = Record<string, string | number | boolean | null>
type ReportPage = { count: number; next: string | null; previous: string | null; results: ReportRow[] }
export type DashboardData = {
  business_date: string
  completed_sales: number
  sales_total: string
  payment_total: string
  active_drug_count: number
  sellable_units: number
  low_stock_drugs: { drug_id: number; name: string; strength: string; available_units: number; reorder_level: number }[]
  expired_batch_count: number
  expiring_batch_count: number
  pending_purchase_orders: number
  top_selling_drugs: { drug_id: number; name: string; units: number }[]
  recent_activity: { action: string; entity_type: string; entity_id: string; occurred_at: string }[]
}

export function DashboardPage({ onNavigate }: { onNavigate: (page: 'Inventory' | 'Purchasing' | 'Point of sale' | 'Reports') => void }) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    apiGet<DashboardData>('/dashboard/summary/').then((summary) => { if (active) setData(summary) })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'Dashboard data could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  if (loading) return <div className="data-loading"><LoaderCircle size={19} className="spin" /> Loading live business metrics</div>
  if (error || !data) return <div className="inline-error" role="alert"><AlertTriangle size={16} />{error || 'Dashboard data is unavailable.'}</div>

  const money = (value: string) => `UGX ${Number(value).toLocaleString('en-UG', { minimumFractionDigits: 2 })}`
  const metrics: { label: string; value: string; detail: string; target: 'Inventory' | 'Purchasing' | 'Point of sale' | 'Reports'; tone: string }[] = [
    { label: 'Sales today', value: money(data.sales_total), detail: `${data.completed_sales} completed transactions`, target: 'Reports', tone: 'metric-green' },
    { label: 'Payments recorded', value: money(data.payment_total), detail: 'Completed sales only', target: 'Reports', tone: 'metric-blue' },
    { label: 'Sellable stock', value: data.sellable_units.toLocaleString('en-UG'), detail: `${data.active_drug_count} active drugs`, target: 'Inventory', tone: 'metric-teal' },
    { label: 'Stock alerts', value: String(data.low_stock_drugs.length + data.expired_batch_count + data.expiring_batch_count), detail: `${data.low_stock_drugs.length} low · ${data.expired_batch_count} expired · ${data.expiring_batch_count} expiring`, target: 'Inventory', tone: 'metric-amber' },
  ]

  return (
    <div className="dashboard-view">
      <section className="metric-grid" aria-label="Today's pharmacy metrics">
        {metrics.map((metric) => <button className={`metric-tile ${metric.tone}`} key={metric.label} onClick={() => onNavigate(metric.target)}><span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.detail}</small></button>)}
      </section>
      <section className="dashboard-banner" aria-label="Pharmacy operations">
        <img src={pharmacyCareBanner} alt="Healthcare professional using a mobile device during pharmacy care" />
        <div className="dashboard-banner-copy">
          <span className="eyebrow">PHARMACY MANAGEMENT SYSTEM</span>
          <h2>Pharmacy care, coordinated.</h2>
          <p>Inventory, prescriptions and dispensing activity in one workspace.</p>
        </div>
        <span className="dashboard-banner-location">SINGLE LOCATION · KAMPALA</span>
      </section>
      <section className="dashboard-lower">
        <div className="dashboard-section"><header><h2>Stock requiring attention</h2><button onClick={() => onNavigate('Inventory')}>Inventory →</button></header>{data.low_stock_drugs.length === 0 ? <p className="dashboard-empty">No low-stock drugs at this time.</p> : <div className="dashboard-list">{data.low_stock_drugs.slice(0, 6).map((item) => <div className="dashboard-list-row" key={item.drug_id}><span><strong>{item.name}</strong><small>{item.strength}</small></span><span className="stock-warning">{item.available_units} / {item.reorder_level} units</span></div>)}</div>}<div className="alert-strip"><AlertTriangle size={15} /><span>{data.expired_batch_count} expired batches · {data.expiring_batch_count} within the warning window</span></div></div>
        <div className="dashboard-section"><header><h2>Today’s top sellers</h2><button onClick={() => onNavigate('Reports')}>Reports →</button></header>{data.top_selling_drugs.length === 0 ? <p className="dashboard-empty">Completed sales will appear here.</p> : <div className="dashboard-list">{data.top_selling_drugs.map((item, index) => <div className="dashboard-list-row" key={item.drug_id}><span className="rank">0{index + 1}</span><strong>{item.name}</strong><span className="seller-units">{item.units} units</span></div>)}</div>}<div className="pending-purchase"><span>Open purchase orders</span><strong>{data.pending_purchase_orders}</strong><button onClick={() => onNavigate('Purchasing')}>Review orders →</button></div></div>
      </section>
    </div>
  )
}

function useDrugs(search: string) {
  const [drugs, setDrugs] = useState<Drug[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    const query = search ? `?search=${encodeURIComponent(search)}` : ''
    apiGet<Drug[] | { results: Drug[] }>(`/drugs/${query}`).then((data) => {
      if (active) setDrugs(Array.isArray(data) ? data : data.results)
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : 'Could not load drug records.')
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [search])

  return { drugs, loading, error }
}

export function InventoryPage() {
  const [search, setSearch] = useState('')
  const { drugs, loading, error } = useDrugs(search)

  return (
    <section className="data-page">
      <div className="data-toolbar"><label className="search-control"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search generic name, brand, or strength" aria-label="Search drugs" /></label><span className="result-count">{loading ? 'Loading…' : `${drugs.length} drug records`}</span></div>
      {error && <div className="inline-error" role="alert"><AlertTriangle size={16} />{error}</div>}
      {loading ? <div className="data-loading"><LoaderCircle size={19} className="spin" /> Loading inventory records</div> : drugs.length === 0 ? <div className="data-empty"><Search size={20} /><strong>No matching drugs</strong><span>Try a different search term or add drugs after sign-in with inventory permissions.</span></div> : (
        <div className="table-wrap"><table><thead><tr><th>Drug</th><th>Category</th><th>Dosage form</th><th>Unit price</th><th>Dispensing</th><th>Status</th></tr></thead><tbody>
          {drugs.map((drug) => <tr key={drug.id}><td><strong>{drug.generic_name}</strong><small>{drug.brand_name || 'Generic'} · {drug.strength}</small></td><td>Category {drug.category}</td><td>{drug.dosage_form}</td><td>UGX {Number(drug.selling_price).toLocaleString('en-UG', { minimumFractionDigits: 2 })}</td><td><span className={`table-badge ${drug.prescription_required ? 'badge-rx' : 'badge-otc'}`}>{drug.prescription_required ? 'Prescription' : 'OTC'}</span></td><td><span className={`status-label ${drug.status}`}>{drug.status}</span></td></tr>)}
        </tbody></table></div>
      )}
    </section>
  )
}

export function PointOfSalePage() {
  const [search, setSearch] = useState('')
  const { drugs, loading, error: loadError } = useDrugs(search)
  const [cart, setCart] = useState<CartLine[]>([])
  const [method, setMethod] = useState('cash')
  const [cash, setCash] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [customerQuery, setCustomerQuery] = useState('')
  const [customerMatches, setCustomerMatches] = useState<CheckoutCustomer[]>([])
  const [customerLookupError, setCustomerLookupError] = useState('')
  const [prescriptionId, setPrescriptionId] = useState('')
  const [eligiblePrescriptions, setEligiblePrescriptions] = useState<EligiblePrescription[]>([])
  const [checkoutError, setCheckoutError] = useState('')
  const [busy, setBusy] = useState(false)
  const [sale, setSale] = useState<SaleResult | null>(null)
  const total = cart.reduce((sum, line) => sum + Number(line.drug.selling_price) * line.quantity, 0)

  useEffect(() => {
    if (customerQuery.trim().length < 2 || customerId) {
      setCustomerMatches([])
      setCustomerLookupError('')
      return
    }
    let active = true
    const timer = window.setTimeout(() => {
      apiGet<CheckoutCustomer[]>(`/sales/customer-lookup/?q=${encodeURIComponent(customerQuery.trim())}`)
        .then((rows) => { if (active) setCustomerMatches(rows) })
        .catch((cause: unknown) => { if (active) setCustomerLookupError(cause instanceof Error ? cause.message : 'Customer lookup failed.') })
    }, 220)
    return () => { active = false; window.clearTimeout(timer) }
  }, [customerQuery, customerId])

  useEffect(() => {
    if (!customerId) {
      setEligiblePrescriptions([])
      setPrescriptionId('')
      return
    }
    let active = true
    apiGet<EligiblePrescription[]>(`/prescriptions/eligible/?customer_id=${customerId}`)
      .then((rows) => { if (active) setEligiblePrescriptions(rows.filter((row) => row.remaining.length > 0)) })
      .catch(() => { if (active) setEligiblePrescriptions([]) })
    return () => { active = false }
  }, [customerId])

  function addDrug(drug: Drug) {
    if (drug.status !== 'active') return
    setSale(null)
    setCart((current) => {
      const existing = current.find((line) => line.drug.id === drug.id)
      return existing ? current.map((line) => line.drug.id === drug.id ? { ...line, quantity: line.quantity + 1 } : line) : [...current, { drug, quantity: 1 }]
    })
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCheckoutError('')
    if (cart.length === 0) return setCheckoutError('Add at least one drug to the sale.')
    if (cart.some((line) => line.drug.prescription_required) && !prescriptionId) return setCheckoutError('A prescription ID is required for prescription-only items.')
    setBusy(true)
    try {
      const result = await apiPost<SaleResult>('/sales/checkout/', {
        customer_id: customerId ? Number(customerId) : null,
        prescription_id: prescriptionId ? Number(prescriptionId) : null,
        items: cart.map((line) => ({ drug_id: line.drug.id, quantity: line.quantity })),
        payment_method: method,
        ...(method === 'cash' ? { cash_tendered: cash } : {}),
      }, crypto.randomUUID())
      setSale(result)
      setCart([])
      setCash('')
      setCustomerId('')
      setCustomerQuery('')
      setPrescriptionId('')
    } catch (cause) {
      setCheckoutError(cause instanceof ApiError ? cause.detail : cause instanceof Error ? cause.message : 'Checkout failed. No sale was recorded.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="pos-layout">
      <div className="pos-catalog">
        <div className="data-toolbar"><label className="search-control"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find a drug by name or strength" aria-label="Find a drug" /></label></div>
        {loadError && <div className="inline-error" role="alert"><AlertTriangle size={16} />{loadError}</div>}
        {loading ? <div className="data-loading"><LoaderCircle size={19} className="spin" /> Loading drug catalogue</div> : <div className="pos-drug-list">{drugs.filter((drug) => drug.status === 'active').map((drug) => <button className="pos-drug" key={drug.id} onClick={() => addDrug(drug)}><span className="pos-drug-add"><Plus size={17} /></span><span className="pos-drug-info"><strong>{drug.generic_name}</strong><small>{drug.strength} · {drug.dosage_form}</small></span><span className="pos-drug-price">UGX {Number(drug.selling_price).toLocaleString('en-UG')}</span>{drug.prescription_required && <span className="table-badge badge-rx">Rx</span>}</button>)}{drugs.length === 0 && <div className="data-empty"><Search size={20} /><strong>No matching drugs</strong><span>Search the catalogue or check your inventory access.</span></div>}</div>}
      </div>
      <form className="pos-checkout" onSubmit={submit}>
        <header className="cart-heading"><span><ShoppingCart size={17} /> Current sale</span><span>{cart.reduce((sum, line) => sum + line.quantity, 0)} units</span></header>
        <div className="cart-lines">{cart.length === 0 ? <div className="cart-empty">Search and add drugs to start a sale.</div> : cart.map((line) => <div className="cart-line" key={line.drug.id}><span className="cart-line-name"><strong>{line.drug.generic_name}</strong><small>UGX {Number(line.drug.selling_price).toLocaleString('en-UG')} each</small></span><input aria-label={`Quantity for ${line.drug.generic_name}`} type="number" min="1" value={line.quantity} onChange={(event) => setCart((current) => current.map((entry) => entry.drug.id === line.drug.id ? { ...entry, quantity: Math.max(1, Number(event.target.value)) } : entry))} /><strong className="cart-line-total">UGX {(Number(line.drug.selling_price) * line.quantity).toLocaleString('en-UG')}</strong><button className="icon-button remove-line" type="button" onClick={() => setCart((current) => current.filter((entry) => entry.drug.id !== line.drug.id))} aria-label={`Remove ${line.drug.generic_name}`}><Trash2 size={15} /></button></div>)}</div>
        <div className="pos-fields">
          <label className="customer-field">Customer (optional for OTC)
            {customerId ? <span className="selected-customer"><span>{customerQuery}</span><button type="button" onClick={() => { setCustomerId(''); setCustomerQuery(''); setEligiblePrescriptions([]); setPrescriptionId('') }}>Change</button></span> : <input value={customerQuery} onChange={(event) => setCustomerQuery(event.target.value)} placeholder="Search name or phone" autoComplete="off" />}
            {customerMatches.length > 0 && <span className="customer-matches">{customerMatches.map((customer) => <button type="button" key={customer.id} onClick={() => { setCustomerId(String(customer.id)); setCustomerQuery(customer.full_name); setCustomerMatches([]) }}>{customer.full_name}</button>)}</span>}
            {customerLookupError && <small className="field-error">{customerLookupError}</small>}
          </label>
          <label>Approved prescription
            <select value={prescriptionId} onChange={(event) => setPrescriptionId(event.target.value)} disabled={!customerId || eligiblePrescriptions.length === 0}>
              <option value="">{customerId ? 'Select for prescription-only drugs' : 'Choose a customer first'}</option>
              {eligiblePrescriptions.map((prescription) => <option key={prescription.id} value={prescription.id}>{prescription.reference} · {prescription.remaining.map((item) => `${item.drug_name}: ${item.remaining_quantity}`).join(', ')}</option>)}
            </select>
          </label>
          <label>Payment method<select value={method} onChange={(event) => setMethod(event.target.value)}><option value="cash">Cash</option><option value="mobile_money">Mobile Money</option><option value="card">Card</option><option value="bank_transfer">Bank Transfer</option></select></label>
          {method === 'cash' && <label>Cash tendered (UGX)<input inputMode="decimal" value={cash} onChange={(event) => setCash(event.target.value)} placeholder="0.00" required={method === 'cash'} /></label>}
        </div>
        {checkoutError && <div className="inline-error checkout-error" role="alert"><AlertTriangle size={16} />{checkoutError}</div>}
        {sale && <div className="checkout-success" role="status"><Check size={16} /><span><strong>Sale completed</strong><small>{sale.sale_number} · UGX {Number(sale.total_amount).toLocaleString('en-UG', { minimumFractionDigits: 2 })}</small></span><button className="icon-button" type="button" aria-label="Print receipt" title="Print receipt" onClick={() => window.print()}><Printer size={16} /></button></div>}
        <div className="checkout-total"><span>Total</span><strong>UGX {total.toLocaleString('en-UG', { minimumFractionDigits: 2 })}</strong></div>
        <button className="checkout-button" type="submit" disabled={busy || cart.length === 0}>{busy ? <><LoaderCircle className="spin" size={17} /> Processing…</> : 'Complete sale'}</button>
        <p className="checkout-note">Stock, prescription allowance, and prices are revalidated by the server.</p>
      </form>
    </section>
  )
}

export function ReportsPage() {
  const [report, setReport] = useState('sales')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [pageNumber, setPageNumber] = useState(1)
  const [data, setData] = useState<ReportPage | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ page: String(pageNumber) })
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    apiGet<ReportPage>(`/reports/${report}/?${params}`).then((result) => { if (active) setData(result) })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'Report could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [report, startDate, endDate, pageNumber])

  const columns = data?.results[0] ? Object.keys(data.results[0]) : []
  return (
    <section className="data-page report-page">
      <div className="report-toolbar"><label>Report<select value={report} onChange={(event) => { setReport(event.target.value); setPageNumber(1) }}><option value="sales">Sales</option><option value="sales-by-drug">Sales by drug</option><option value="payments">Payments</option><option value="stock">Current stock</option><option value="batches">Stock by batch</option><option value="purchases">Purchases</option><option value="movements">Stock movements</option></select></label><label>From<input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setPageNumber(1) }} /></label><label>To<input type="date" value={endDate} onChange={(event) => { setEndDate(event.target.value); setPageNumber(1) }} /></label><button className="report-action" onClick={async () => { try { const result = await apiGet<string>(`/reports/${report}/?export=csv${startDate ? `&start_date=${startDate}` : ''}${endDate ? `&end_date=${endDate}` : ''}`); const blob = new Blob([result], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${report}.csv`; anchor.click(); URL.revokeObjectURL(url) } catch (cause) { setError(cause instanceof Error ? cause.message : 'CSV export failed.') } }}><ArrowDownToLine size={15} /> CSV</button><button className="report-action" onClick={() => window.print()}><Printer size={15} /> Print</button></div>
      {error && <div className="inline-error" role="alert"><AlertTriangle size={16} />{error}</div>}
      {loading ? <div className="data-loading"><LoaderCircle className="spin" size={19} /> Loading report records</div> : !data || columns.length === 0 ? <div className="data-empty"><Printer size={20} /><strong>No report rows</strong><span>Records matching this report will appear after authorized pharmacy activity.</span></div> : <div className="table-wrap"><table><thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{data.results.map((row, index) => <tr key={String(row.id ?? row.sale_number ?? row.batch_id ?? index)}>{columns.map((column) => <td key={column}>{typeof row[column] === 'boolean' ? (row[column] ? 'Yes' : 'No') : String(row[column] ?? '—')}</td>)}</tr>)}</tbody></table></div>}
      {data && <div className="report-pagination"><span>{data.count} records</span><div><button disabled={!data.previous || loading} onClick={() => setPageNumber((current) => Math.max(1, current - 1))}>Previous</button><span>Page {pageNumber}</span><button disabled={!data.next || loading} onClick={() => setPageNumber((current) => current + 1)}>Next</button></div></div>}
    </section>
  )
}
