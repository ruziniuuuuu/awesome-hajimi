#!/usr/bin/env python3
"""
Bilibili Hajimi Video Fetcher
Fetches videos related to "哈基米" (Hajimi) from Bilibili and generates a README.md table.
"""

import asyncio
import sys
import os
import aiohttp
from datetime import datetime
from typing import List, Dict, Any
from bilibili_api import search, video, Credential
from bilibili_api.exceptions import *


class HajimiVideoFetcher:
    def __init__(self):
        self.videos_data = []
        self.assets_dir = "assets/covers"
        # Create assets directory if it doesn't exist
        os.makedirs(self.assets_dir, exist_ok=True)
    
    async def search_hajimi_videos(self, keyword: str = "哈基米", total_videos: int = 100) -> List[Dict[str, Any]]:
        """Search for Hajimi related videos"""
        try:
            print(f"Searching for '{keyword}' videos (target: {total_videos})...")
            
            all_videos = []
            page = 1
            page_size = 50  # Max per page
            
            while len(all_videos) < total_videos:
                print(f"Fetching page {page}...")
                
                # Search for videos with the keyword
                result = await search.search_by_type(
                    keyword=keyword,
                    search_type=search.SearchObjectType.VIDEO,
                    page=page,
                    page_size=page_size,
                    order_type=search.OrderVideo.TOTALRANK  # Sort by popularity
                )
                
                if not result:
                    print("No more search results found")
                    break
                
                # Handle different possible result structures
                if 'result' in result:
                    videos = result['result']
                elif 'data' in result and 'result' in result['data']:
                    videos = result['data']['result']
                else:
                    print(f"Unexpected result structure: {list(result.keys())}")
                    break
                
                if not videos:
                    print("No more videos available")
                    break
                
                all_videos.extend(videos)
                print(f"Collected {len(all_videos)} videos so far...")
                
                # Break if we got less than page_size results (end of results)
                if len(videos) < page_size:
                    break
                    
                page += 1
                await asyncio.sleep(1)  # Rate limiting between pages
            
            # Truncate to requested number
            all_videos = all_videos[:total_videos]
            print(f"Found {len(all_videos)} videos total")
            
            return all_videos
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    async def download_cover(self, cover_url: str, bvid: str) -> str:
        """Download video cover and return local path"""
        try:
            # Convert relative URL to absolute URL
            if cover_url.startswith('//'):
                cover_url = 'https:' + cover_url
            elif cover_url.startswith('/'):
                cover_url = 'https://i0.hdslb.com' + cover_url
            
            # Extract file extension from URL
            file_ext = '.jpg'  # Default to jpg
            if '.' in cover_url:
                file_ext = '.' + cover_url.split('.')[-1].split('?')[0]
            
            # Create filename using bvid
            filename = f"{bvid}{file_ext}"
            filepath = os.path.join(self.assets_dir, filename)
            
            # Skip download if file already exists
            if os.path.exists(filepath):
                return f"assets/covers/{filename}"
            
            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(cover_url) as response:
                    if response.status == 200:
                        with open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        print(f"Downloaded cover: {filename}")
                        return f"assets/covers/{filename}"
                    else:
                        print(f"Failed to download cover for {bvid}: HTTP {response.status}")
                        return cover_url  # Return original URL as fallback
        
        except Exception as e:
            print(f"Error downloading cover for {bvid}: {e}")
            return cover_url  # Return original URL as fallback
    
    async def get_video_details(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get detailed information for each video"""
        detailed_videos = []
        
        for i, video_info in enumerate(videos):
            try:
                print(f"Processing video {i+1}/{len(videos)}...")
                
                # Extract basic info from search result
                bvid = video_info.get('bvid', '')
                if not bvid:
                    continue
                
                # Get detailed video information
                v = video.Video(bvid=bvid)
                detail = await v.get_info()
                
                # Download cover image
                cover_url = video_info.get('pic', '')
                local_cover_path = await self.download_cover(cover_url, bvid)
                
                # Extract publish date (timestamp to datetime)
                pub_timestamp = detail.get('pubdate', 0)
                if pub_timestamp:
                    publish_date = datetime.fromtimestamp(pub_timestamp)
                    formatted_date = publish_date.strftime('%Y-%m-%d')
                else:
                    publish_date = datetime.min  # For sorting purposes
                    formatted_date = "未知"
                
                # Extract the information we need
                video_data = {
                    'title': video_info.get('title', '').replace('<em class="keyword">', '').replace('</em>', ''),
                    'bvid': bvid,
                    'cover': local_cover_path,
                    'view_count': detail.get('stat', {}).get('view', 0),
                    'url': f"https://www.bilibili.com/video/{bvid}",
                    'publish_date': publish_date,
                    'formatted_date': formatted_date
                }
                
                detailed_videos.append(video_data)
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing video {video_info.get('bvid', 'unknown')}: {e}")
                continue
        
        # Sort by publish date (newest first)
        detailed_videos.sort(key=lambda x: x['publish_date'], reverse=True)
        print(f"Videos sorted by publish date (newest first)")
        
        return detailed_videos
    
    def format_view_count(self, count: int) -> str:
        """Format view count in a human-readable way"""
        if count >= 10000:
            return f"{count/10000:.1f}万"
        else:
            return str(count)
    
    def generate_readme_content(self, videos: List[Dict[str, Any]]) -> str:
        """Generate README.md content with video table"""
        
        content = """# awesome-hajimi
collections of hajimi (哈基米 in Chinese) on the Internet.

## 视频列表 (Video List)

| 视频标题 (Title) | 封面 | 播放量 (Views) | 发布日期 (Date) |
|---|---|---|---|
"""
        
        for video in videos:
            title_with_link = f"[{video['title']}]({video['url']})"
            # Use local cover path with smaller size (120px width)
            cover_path = video['cover']
            if cover_path:
                cover_img = f'<img src="{cover_path}" alt="cover" width="120">'
            else:
                cover_img = "无封面"
            view_count = self.format_view_count(video['view_count'])
            publish_date = video['formatted_date']
            
            content += f"| {title_with_link} | {cover_img} | {view_count} | {publish_date} |\n"
        
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        content += f"""
---
*最后更新: {current_time} (自动生成)*
*数据来源: [Bilibili](https://www.bilibili.com)*

## 使用说明

运行以下命令更新视频列表:
```bash
python3 fetch_hajimi_videos.py
```
"""
        
        return content
    
    async def run(self):
        """Main execution function"""
        try:
            # Search for videos (100 videos)
            videos = await self.search_hajimi_videos(total_videos=100)
            
            if not videos:
                print("No videos found!")
                return
            
            # Get detailed information
            detailed_videos = await self.get_video_details(videos)
            
            if not detailed_videos:
                print("No detailed video information could be retrieved!")
                return
            
            print(f"Successfully processed {len(detailed_videos)} videos")
            
            # Generate README content
            readme_content = self.generate_readme_content(detailed_videos)
            
            # Write to README.md
            with open('README.md', 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            print("README.md has been updated successfully!")
            
        except Exception as e:
            print(f"Error in main execution: {e}")
            sys.exit(1)


async def main():
    fetcher = HajimiVideoFetcher()
    await fetcher.run()


if __name__ == "__main__":
    asyncio.run(main())