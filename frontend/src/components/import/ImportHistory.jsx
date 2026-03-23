import React from 'react';
import useImageStore from '../../store/useImageStore';
import Card from '../common/Card';
import Badge from '../common/Badge';
import { formatDate } from '../../utils/formatters';
import { History, CheckCircle, XCircle, Clock, Image as ImageIcon, RefreshCw } from 'lucide-react';

const ImportHistory = () => {
    const { importHistory, recomputeAllFeatures, recomputing } = useImageStore();

    const statusIcons = {
        completed: <CheckCircle className="w-4 h-4" />,
        failed: <XCircle className="w-4 h-4" />,
        processing: <Clock className="w-4 h-4 animate-spin" />,
    };

    const statusVariants = {
        completed: 'success',
        failed: 'error',
        processing: 'warning',
    };

    return (
        <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <History className="w-5 h-5 text-primary-400" />
                    <h3 className="text-xl font-semibold text-white">Import Results & History</h3>
                </div>
                <button
                    onClick={recomputeAllFeatures}
                    disabled={recomputing || importHistory.length === 0}
                    className="flex items-center px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded border border-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                    <RefreshCw className={`w-4 h-4 mr-2 ${recomputing ? 'animate-spin' : ''}`} />
                    Recompute All
                </button>
            </div>

            {importHistory.length === 0 ? (
                <div className="text-center py-8 text-slate-400 bg-slate-800/20 rounded-lg border border-dashed border-slate-700">
                    <p>No import history yet. Drag and drop images above to start.</p>
                </div>
            ) : (
                <div className="flex flex-col gap-4 overflow-y-auto pr-2">
                    {importHistory.map((item) => (
                        <div
                            key={item.id}
                            className="bg-slate-800/50 border border-slate-700/50 rounded-lg overflow-hidden hover:border-slate-500/50 transition-all flex flex-row h-[300px] group"
                        >
                            {/* Image Preview - Left */}
                            <div className="relative w-[300px] aspect-square flex-shrink-0 bg-slate-900 flex items-center justify-center overflow-hidden">
                                {item.previewUrl ? (
                                    <img
                                        src={item.previewUrl}
                                        alt={item.file_name}
                                        className="w-full h-full object-cover transition-transform group-hover:scale-105"
                                    />
                                ) : (
                                    <ImageIcon className="w-12 h-12 text-slate-600" />
                                )}

                                <div className="absolute top-2 right-2">
                                    <Badge variant={statusVariants[item.status || 'completed']}>
                                        {item.status || 'completed'}
                                    </Badge>
                                </div>
                            </div>

                            {/* Metadata - Right */}
                            <div className="p-4 flex-1 flex flex-col justify-between">
                                <div className="flex items-start">
                                    <div className="flex-1 min-w-0">
                                        <h4 className="font-medium text-white text-base mb-1 truncate" title={item.file_name}>
                                            {item.file_name}
                                        </h4>
                                        <p className="text-sm text-slate-400 font-mono">
                                            {item.width} × {item.height}
                                        </p>
                                    </div>
                                </div>

                                {/* Stats Grid */}
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mb-2">
                                    <div className="flex flex-col">
                                        <span className="text-slate-500 text-xs mb-1">Brightness</span>
                                        <span className="text-slate-200 font-medium">{(item.brightness * 100).toFixed(1)}%</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-slate-500 text-xs mb-1">Contrast</span>
                                        <span className="text-slate-200 font-medium">{(item.contrast * 100).toFixed(1)}%</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-slate-500 text-xs mb-1">Saturation</span>
                                        <span className="text-slate-200 font-medium">
                                            {item.saturation !== undefined ? (item.saturation * 100).toFixed(1) + '%' : 'N/A'}
                                        </span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-slate-500 text-xs mb-1">Edge Density</span>
                                        <span className="text-slate-200 font-medium">{(item.edge_density * 100).toFixed(1)}%</span>
                                    </div>

                                    <div className="flex flex-col">
                                        <span className="text-slate-500 text-xs mb-1">Uploaded</span>
                                        <span className="text-slate-200 font-medium text-xs whitespace-nowrap">
                                            {item.created_at ? formatDate(item.created_at) : 'Just now'}
                                        </span>
                                    </div>
                                </div>

                                {/* Raw Features JSON */}
                                {item.features_json && (
                                    <div className="mt-auto pt-2 border-t border-slate-700/50 flex flex-col flex-1 min-h-0">
                                        <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider mb-1">Raw Features</span>
                                        <div className="bg-slate-950/50 rounded p-2 overflow-y-auto text-[10px] font-mono text-slate-400 border border-slate-800/50">
                                            <pre className="whitespace-pre-wrap break-all">
                                                {JSON.stringify(item.features_json, null, 2)}
                                            </pre>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </Card>
    );
};

export default ImportHistory;
