import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, Award, Clock, FileCheck, FileText, Calendar, 
  Search, Filter, Plus, Download, Upload, Eye, ChevronDown, 
  ChevronUp, CheckCircle, AlertTriangle, AlertCircle, Bell, 
  Mail, MessageSquare, Send, Check, Settings, ArrowUpRight,
  TrendingUp, Users, Building, ExternalLink, RefreshCw
} from 'lucide-react';

/* ==========================================================================
   OctaQube ENTERPRISE COMPLIANCE STANDARDS REACT MODULE
   Microsoft Admin Center / Atlassian / Linear Minimal Enterprise Theme
   ========================================================================== */

export const ComplianceKPICard = ({ title, value, trend, icon: Icon, trendType }) => (
  <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
    <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-900 mb-3">
      <Icon className="w-5 h-5" />
    </div>
    <div className="text-sm font-medium text-gray-500 mb-1">{title}</div>
    <div className="flex items-baseline justify-between">
      <span className="text-3xl font-bold tracking-tight text-gray-900">{value}</span>
      <span className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full ${
        trendType === 'up' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-gray-100 text-gray-700'
      }`}>
        {trend}
      </span>
    </div>
  </div>
);

export const StatusBadge = ({ status }) => {
  const statusConfig = {
    certified: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Certified' },
    pending: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'Pending Audit' },
    expired: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', label: 'Expired' },
    notconfigured: { bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200', label: 'Not Configured' }
  };
  const config = statusConfig[status] || statusConfig.notconfigured;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${config.bg} ${config.text} ${config.border}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {config.label}
    </span>
  );
};

export const ExpandableCardDetails = ({ item }) => (
  <div className="mt-5 pt-5 border-t border-gray-200 grid grid-cols-1 md:grid-cols-3 gap-6 text-sm text-gray-700 animate-fadeIn">
    <div>
      <h5 className="font-semibold text-gray-900 mb-2">Framework Scope</h5>
      <p className="text-xs text-gray-600 leading-relaxed">{item.scope || 'Full organizational boundary covering quality systems, manufacturing execution, and supply chain governance.'}</p>
    </div>
    <div>
      <h5 className="font-semibold text-gray-900 mb-2">Auditors & Personnel</h5>
      <div className="space-y-1 text-xs">
        <div><span className="text-gray-500">Internal Auditor:</span> <strong className="text-gray-900">{item.internalAuditor || 'Sarah Jenkins (Lead)'}</strong></div>
        <div><span className="text-gray-500">External Auditor:</span> <strong className="text-gray-900">{item.externalAuditor || 'BSI Group (Registrar)'}</strong></div>
        <div><span className="text-gray-500">Primary Owner:</span> <strong className="text-gray-900">{item.owner || 'Quality Operations Team'}</strong></div>
      </div>
    </div>
    <div>
      <h5 className="font-semibold text-gray-900 mb-2">Compliance Checkpoints</h5>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {(item.departments || ['QA', 'Manufacturing', 'Operations']).map((dept, i) => (
          <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-md">{dept}</span>
        ))}
      </div>
      <div className="text-xs text-gray-500">Linked Projects: <span className="font-medium text-gray-900">{item.linkedProjects || '3 Active DMAIC / 8D Projects'}</span></div>
    </div>
  </div>
);

export const ComplianceStandardCard = ({ item, onPreview, onUpload }) => {
  const [expanded, setExpanded] = useState(false);
  const [checked, setChecked] = useState(item.status === 'certified');

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-all duration-200 mb-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gray-900 text-white flex items-center justify-center shrink-0">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h4 className="text-lg font-bold text-gray-900">{item.name}</h4>
              <StatusBadge status={checked ? 'certified' : item.status} />
            </div>
            <p className="text-sm text-gray-500 mt-0.5">{item.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="relative inline-flex items-center cursor-pointer me-2">
            <input 
              type="checkbox" 
              checked={checked} 
              onChange={(e) => setChecked(e.target.checked)} 
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gray-900" />
          </label>
          <button onClick={() => onPreview(item)} className="px-3 py-1.5 text-xs font-semibold text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg flex items-center gap-1.5 transition">
            <Eye className="w-3.5 h-3.5" /> Preview
          </button>
          <button onClick={() => onUpload(item)} className="px-3 py-1.5 text-xs font-semibold text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg flex items-center gap-1.5 transition">
            <Upload className="w-3.5 h-3.5" /> Upload
          </button>
          <button onClick={() => setExpanded(!expanded)} className="px-3 py-1.5 text-xs font-semibold text-gray-900 bg-white hover:bg-gray-50 border border-gray-300 rounded-lg flex items-center gap-1.5 transition">
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {expanded ? 'Hide' : 'Details'}
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6 pt-5 border-t border-gray-100 text-xs">
        <div>
          <span className="text-gray-400 block uppercase tracking-wider font-semibold">Certificate No</span>
          <span className="font-semibold text-gray-900">{item.certNo || 'OctaQube-2026-001'}</span>
        </div>
        <div>
          <span className="text-gray-400 block uppercase tracking-wider font-semibold">Issue Date</span>
          <span className="font-semibold text-gray-900">{item.issueDate || '12 Jan 2026'}</span>
        </div>
        <div>
          <span className="text-gray-400 block uppercase tracking-wider font-semibold">Expiry Date</span>
          <span className="font-semibold text-gray-900">{item.expiryDate || '12 Jan 2029'}</span>
        </div>
        <div>
          <span className="text-gray-400 block uppercase tracking-wider font-semibold">Last Audit</span>
          <span className="font-semibold text-gray-900">{item.lastAudit || 'May 2026'}</span>
        </div>
        <div>
          <span className="text-gray-400 block uppercase tracking-wider font-semibold">Next Audit</span>
          <span className="font-semibold text-gray-900">{item.nextAudit || 'Nov 2026'}</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs font-semibold mb-1">
          <span className="text-gray-600">Audit Compliance Score</span>
          <span className="text-gray-900">{item.score || 92}%</span>
        </div>
        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full bg-gray-900 rounded-full transition-all duration-500" style={{ width: `${item.score || 92}%` }} />
        </div>
      </div>

      {expanded && <ExpandableCardDetails item={item} />}
    </div>
  );
};

export default function ComplianceEnterpriseView() {
  const [activeFilter, setActiveFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [selectedCert, setSelectedCert] = useState(null);

  const standardsData = [
    { id: 'iso9001', name: 'ISO 9001:2015', description: 'Quality Management System Standard', status: 'certified', certNo: 'OctaQube-2026-0001', issueDate: '12 Jan 2026', expiryDate: '12 Jan 2029', lastAudit: 'May 2026', nextAudit: 'Nov 2026', score: 95, departments: ['QA', 'Manufacturing', 'Ops'] },
    { id: 'iso14001', name: 'ISO 14001:2015', description: 'Environmental Management System', status: 'certified', certNo: 'OctaQube-2026-0002', issueDate: '10 Feb 2025', expiryDate: '10 Feb 2028', lastAudit: 'Apr 2026', nextAudit: 'Oct 2026', score: 88, departments: ['EHS', 'Facilities', 'Ops'] },
    { id: 'as9100', name: 'AS9100 Rev D', description: 'Aerospace Quality Management System', status: 'pending', certNo: 'OctaQube-2026-0003', issueDate: '01 Mar 2024', expiryDate: '01 Mar 2027', lastAudit: 'Dec 2025', nextAudit: 'Aug 2026', score: 72, departments: ['Aerospace', 'QA'] },
    { id: 'iatf16949', name: 'IATF 16949:2016', description: 'Automotive Quality Management System', status: 'pending', certNo: 'OctaQube-2026-0004', issueDate: '15 Jun 2025', expiryDate: '15 Jun 2028', lastAudit: 'Jan 2026', nextAudit: 'Sep 2026', score: 84, departments: ['Automotive', 'Plant A'] },
    { id: 'soc2', name: 'SOC 2 Type II', description: 'Security, Availability & Confidentiality Trust Criteria', status: 'certified', certNo: 'OctaQube-2026-0005', issueDate: '01 Jan 2026', expiryDate: '01 Jan 2027', lastAudit: 'Jun 2026', nextAudit: 'Dec 2026', score: 96, departments: ['IT', 'InfoSec', 'Engineering'] },
    { id: 'iso27001', name: 'ISO 27001:2022', description: 'Information Security Management System', status: 'notconfigured', certNo: 'N/A', issueDate: 'N/A', expiryDate: 'N/A', lastAudit: 'N/A', nextAudit: 'N/A', score: 40, departments: ['InfoSec', 'IT'] }
  ];

  const filteredStandards = standardsData.filter(item => {
    const matchesFilter = activeFilter === 'all' || item.status === activeFilter;
    const matchesSearch = !search || item.name.toLowerCase().includes(search.toLowerCase()) || item.description.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-[#F8F9FB] p-6 font-sans text-gray-900">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Compliance Standards</h1>
          <p className="text-sm text-gray-500 mt-1">Manage regulatory governance, certification lifecycles, and audit readiness across enterprise operations.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2.5 bg-gray-900 text-white font-semibold text-sm rounded-xl hover:bg-gray-800 transition shadow-sm flex items-center gap-2">
            <Plus className="w-4 h-4" /> Add Standard
          </button>
          <button className="px-4 py-2.5 bg-white border border-gray-200 text-gray-900 font-semibold text-sm rounded-xl hover:bg-gray-50 transition shadow-sm flex items-center gap-2">
            <FileText className="w-4 h-4" /> Generate Report
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-8">
        <ComplianceKPICard title="Compliance Score" value="92%" trend="+3.4%" icon={ShieldCheck} trendType="up" />
        <ComplianceKPICard title="Active Standards" value="6" trend="+1 new" icon={Award} trendType="up" />
        <ComplianceKPICard title="Pending Audits" value="2" trend="14 days" icon={Clock} trendType="neutral" />
        <ComplianceKPICard title="Certificates" value="8" trend="1 exp" icon={FileCheck} trendType="neutral" />
        <ComplianceKPICard title="Documents" value="48" trend="12 upd" icon={FileText} trendType="up" />
        <ComplianceKPICard title="Upcoming Audits" value="3" trend="Nov 15" icon={Calendar} trendType="neutral" />
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Workspace Column */}
        <div className="lg:col-span-8 space-y-6">
          {/* Search & Filter Controls */}
          <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-3.5" />
              <input 
                type="text" 
                placeholder="Search standards, frameworks, or certificates..." 
                value={search} 
                onChange={(e) => setSearch(e.target.value)} 
                className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-gray-900 focus:bg-white transition"
              />
            </div>
            <div className="flex items-center gap-2 overflow-x-auto">
              {['all', 'certified', 'pending', 'expired', 'notconfigured'].map(f => (
                <button key={f} onClick={() => setActiveFilter(f)} className={`px-3 py-1.5 rounded-full text-xs font-semibold capitalize whitespace-nowrap transition ${
                  activeFilter === f ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-600 border border-gray-200 hover:border-gray-300'
                }`}>
                  {f === 'notconfigured' ? 'Not Configured' : f}
                </button>
              ))}
            </div>
          </div>

          {/* Cards List */}
          <div>
            {filteredStandards.map(item => (
              <ComplianceStandardCard 
                key={item.id} 
                item={item} 
                onPreview={(cert) => setSelectedCert(cert)} 
                onUpload={(cert) => alert(`Upload triggered for ${cert.name}`)} 
              />
            ))}
          </div>
        </div>

        {/* Right Sticky Intelligence Panel */}
        <div className="lg:col-span-4 space-y-6">
          {/* Overall Compliance Progress Ring Card */}
          <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Score Breakdown</h3>
            <div className="flex items-center justify-center my-4">
              <div className="relative w-36 h-36 flex items-center justify-center rounded-full border-8 border-gray-900 text-3xl font-extrabold text-gray-900">
                92%
              </div>
            </div>
            <div className="space-y-3 mt-6 text-xs font-medium">
              <div>
                <div className="flex justify-between mb-1"><span className="text-gray-600">ISO 9001:2015</span><span className="text-gray-900 font-bold">95%</span></div>
                <div className="w-full h-1.5 bg-gray-100 rounded-full"><div className="h-full bg-gray-900 rounded-full" style={{ width: '95%' }} /></div>
              </div>
              <div>
                <div className="flex justify-between mb-1"><span className="text-gray-600">ISO 14001:2015</span><span className="text-gray-900 font-bold">88%</span></div>
                <div className="w-full h-1.5 bg-gray-100 rounded-full"><div className="h-full bg-emerald-600 rounded-full" style={{ width: '88%' }} /></div>
              </div>
              <div>
                <div className="flex justify-between mb-1"><span className="text-gray-600">AS9100 Rev D</span><span className="text-gray-900 font-bold">72%</span></div>
                <div className="w-full h-1.5 bg-gray-100 rounded-full"><div className="h-full bg-amber-500 rounded-full" style={{ width: '72%' }} /></div>
              </div>
            </div>
          </div>

          {/* Upcoming Audits Timeline Card */}
          <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Upcoming Audits</h3>
            <div className="space-y-4 text-xs">
              {[
                { name: 'ISO 9001 Surveillance Audit', date: '12 Aug 2026', status: 'Scheduled' },
                { name: 'ISO 14001 Recertification', date: '20 Sep 2026', status: 'Scheduled' },
                { name: 'AS9100 Stage 2 Assessment', date: '15 Oct 2026', status: 'Scheduled' },
                { name: 'SOC 2 Type II Evaluation', date: '05 Nov 2026', status: 'Preparation' }
              ].map((a, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
                  <div>
                    <div className="font-semibold text-gray-900">{a.name}</div>
                    <div className="text-gray-500 text-[11px]">{a.date}</div>
                  </div>
                  <span className="px-2 py-1 bg-gray-200 text-gray-800 font-medium rounded-md text-[10px]">{a.status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Expiry Notification Settings Card */}
          <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Expiry Notifications</h3>
            <p className="text-xs text-gray-500 mb-4">Configure automatic alerts before certificate expiration.</p>
            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-gray-700 mb-1">Alert Horizon</label>
                <select className="w-full p-2 bg-gray-50 border border-gray-200 rounded-lg font-medium text-gray-900">
                  <option>30 Days Before Expiry</option>
                  <option>60 Days Before Expiry</option>
                  <option>90 Days Before Expiry</option>
                </select>
              </div>
              <div className="space-y-2 pt-2">
                {['Email Digest', 'SMS Emergency Alerts', 'Microsoft Teams Integration', 'Slack Workflow Channel'].map((ch, i) => (
                  <label key={i} className="flex items-center justify-between cursor-pointer">
                    <span className="text-gray-700 font-medium">{ch}</span>
                    <input type="checkbox" defaultChecked={i === 0 || i === 2} className="rounded border-gray-300 text-gray-900 focus:ring-gray-900" />
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
