import React from 'react';
import useImageStore from '../../store/useImageStore';
import Card from '../common/Card';
import Badge from '../common/Badge';
import { formatDate } from '../../utils/formatters';
import { Image as ImageIcon } from 'lucide-react';

const SimilarityResults = () => {
    const { similarityResults, similarityLoading, queryImageFeatures, queryImagePreviewUrl } = useImageStore();

    if (similarityResults.length === 0 && !similarityLoading) {
        return null;
    }

    return (
        <Card className="p-6">
            <h3 className="text-xl font-semibold text-white mb-6">Search Results</h3>

            {/* Display Query Image Features if available */}
            {queryImageFeatures && (
                <div className="mb-8">
                    <h4 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Query Image Features</h4>
                    <div className="bg-slate-800/80 border border-primary-500/50 rounded-lg overflow-hidden flex flex-row h-[300px]">
                        {/* Image Preview - Left */}
                        <div className="relative w-[300px] aspect-square flex-shrink-0 bg-slate-900 flex items-center justify-center overflow-hidden">
                            {queryImagePreviewUrl ? (
                                <img
                                    src={queryImagePreviewUrl}
                                    alt="Query Image"
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                <ImageIcon className="w-12 h-12 text-slate-600" />
                            )}
                            {/* Input Badge */}
                            <div className="absolute top-2 left-2 bg-primary-500 text-white text-xs px-2 py-1 rounded font-mono shadow-lg shadow-black/50">
                                INPUT IMAGE
                            </div>
                        </div>

                        {/* Metadata - Right */}
                        <div className="p-4 flex-1 flex flex-col justify-between">
                            <div className="flex items-start">
                                <div className="flex-1 min-w-0">
                                    <h4 className="font-medium text-white text-base mb-1 truncate">
                                        Query Image
                                    </h4>
                                    <p className="text-sm text-slate-400 font-mono">
                                        {queryImageFeatures.width} × {queryImageFeatures.height}
                                    </p>
                                </div>
                            </div>

                            {/* Stats Grid */}
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mb-2">
                                <div className="flex flex-col">
                                    <span className="text-slate-500 text-xs mb-1">Brightness</span>
                                    <span className="text-slate-200 font-medium">{(queryImageFeatures.brightness * 100).toFixed(1)}%</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-slate-500 text-xs mb-1">Contrast</span>
                                    <span className="text-slate-200 font-medium">{(queryImageFeatures.contrast * 100).toFixed(1)}%</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-slate-500 text-xs mb-1">Saturation</span>
                                    <span className="text-slate-200 font-medium">
                                        {queryImageFeatures.saturation !== undefined ? (queryImageFeatures.saturation * 100).toFixed(1) + '%' : 'N/A'}
                                    </span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-slate-500 text-xs mb-1">Edge Density</span>
                                    <span className="text-slate-200 font-medium">{(queryImageFeatures.edge_density * 100).toFixed(1)}%</span>
                                </div>

                                 <div className="flex flex-col">
                                    <span className="text-slate-500 text-xs mb-1">Status</span>
                                    <span className="text-primary-400 font-medium text-xs whitespace-nowrap">
                                        Extracted for search
                                    </span>
                                </div>
                            </div>

                             {/* Raw Features JSON */}
                             {queryImageFeatures.features_json && (
                                <div className="mt-auto pt-2 border-t border-slate-700/50 flex flex-col flex-1 min-h-0">
                                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider mb-1">Raw Features</span>
                                    <div className="bg-slate-950/50 rounded p-2 overflow-y-auto text-[10px] font-mono text-slate-400 border border-slate-800/50">
                                        <pre className="whitespace-pre-wrap break-all">
                                            {JSON.stringify(queryImageFeatures.features_json, null, 2)}
                                        </pre>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            <div className="flex flex-col gap-4 overflow-y-auto pr-2">
                {similarityResults.map((item, index) => (
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
                            
                            {/* Similarity Badge Overlay */}
                            <div className="absolute top-2 right-2">
                                <Badge variant={item.similarity > 80 ? 'success' : item.similarity > 50 ? 'warning' : 'default'} className="text-sm font-bold shadow-lg shadow-black/50">
                                    {item.similarity.toFixed(1)}% Match
                                </Badge>
                            </div>
                            
                            {/* Rank Badge overlay */}
                            <div className="absolute top-2 left-2 bg-slate-900/80 text-white text-xs px-2 py-1 rounded font-mono shadow-lg shadow-black/50">
                                #{index + 1}
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
                                        {item.created_at ? formatDate(item.created_at) : 'N/A'}
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
        </Card>
    );
};

export default SimilarityResults;
