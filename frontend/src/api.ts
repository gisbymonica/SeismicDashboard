import type {Asset,Cluster,Earthquake,FeatureImportance,HotspotPrediction,ModelMetadata,PopulationExposure,Summary} from './types'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '')

const buildUrl = (path:string) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return apiBaseUrl ? `${apiBaseUrl}${normalizedPath}` : normalizedPath
}

const json = async <T,>(url:string):Promise<T> => {
  const r = await fetch(buildUrl(url))
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export async function loadDashboard(days=30){
 const [eq,cl,pop,infra,summary]=await Promise.all([
  json<{items:Earthquake[]}>('/api/earthquakes?days='+days),json<{items:Cluster[]}>('/api/clusters?days='+days),json<{items:PopulationExposure[]}>('/api/exposure/population?days='+days),json<{items:Asset[]}>('/api/exposure/infrastructure?days='+days),json<Summary>('/api/summary')]);
 return {earthquakes:eq.items,clusters:cl.items,population:pop.items,assets:infra.items,summary}
}

export async function loadMl(){
 const [predictions,importance,metadata]=await Promise.all([
  json<{items:HotspotPrediction[];status:string}>('/api/ml/hotspot-predictions'),
  json<{items:FeatureImportance[];status:string}>('/api/ml/feature-importance'),
  json<ModelMetadata>('/api/ml/model-metadata')]);
 return {predictions:predictions.items,importance:importance.items,metadata,status:metadata.status}
}

export async function loadHotspotExposure(cellId:string){
 return json<Partial<HotspotPrediction>>('/api/ml/hotspot-predictions/'+encodeURIComponent(cellId)+'/exposure')
}
