import PropTypes from 'prop-types';
import { Play, Clock, Eye, Calendar, Tv } from 'lucide-react';

/**
 * VideoPreview - Card de preview do vídeo do YouTube
 * @param {Object} props
 * @param {Object} props.video - Dados do vídeo
 */
function VideoPreview({ video }) {
  if (!video) return null;

  return (
    <div
      className="bg-off-white rounded-lg p-4 border border-light-gray"
      role="article"
      aria-label={`Preview do vídeo: ${video.title}`}
    >
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Thumbnail */}
        <div className="relative flex-shrink-0 w-full sm:w-48 aspect-video sm:aspect-auto sm:h-28 rounded-lg overflow-hidden bg-dark-gray">
          <img
            src={video.thumbnail}
            alt={`Thumbnail de ${video.title}`}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.src = `https://img.youtube.com/vi/${video.videoId}/hqdefault.jpg`;
            }}
          />
          {/* Play overlay */}
          <div className="absolute inset-0 flex items-center justify-center bg-black/30">
            <div className="w-12 h-12 rounded-full bg-white/90 flex items-center justify-center">
              <Play className="w-6 h-6 text-dark-gray ml-1" aria-hidden="true" />
            </div>
          </div>
          {/* Duration badge */}
          <span className="absolute bottom-2 right-2 px-2 py-0.5 bg-black/80 text-white text-xs font-medium rounded">
            {video.duration}
          </span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-dark-gray text-lg leading-tight mb-2 line-clamp-2">
            {video.title}
          </h3>

          <div className="space-y-1.5 text-sm text-medium-gray">
            <div className="flex items-center gap-2">
              <Tv className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              <span className="truncate">{video.channel}</span>
            </div>

            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              <span>{video.duration} de duração</span>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                <span>{video.views} visualizações</span>
              </div>

              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                <span>Publicado {video.publishedAt}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

VideoPreview.propTypes = {
  video: PropTypes.shape({
    videoId: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    channel: PropTypes.string.isRequired,
    thumbnail: PropTypes.string.isRequired,
    duration: PropTypes.string.isRequired,
    views: PropTypes.string.isRequired,
    publishedAt: PropTypes.string.isRequired
  })
};

export default VideoPreview;
