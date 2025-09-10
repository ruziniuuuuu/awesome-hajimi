#!/usr/bin/env python3
"""
Bilibili Hajimi Video Fetcher
Fetches videos related to "哈基米" (Hajimi) from Bilibili and generates a README.md table.
"""

import asyncio
import sys
from typing import List, Dict, Any
from bilibili_api import search, video, Credential
from bilibili_api.exceptions import *


class HajimiVideoFetcher:
    def __init__(self):
        self.videos_data = []
    
    async def search_hajimi_videos(self, keyword: str = "哈基米", page_size: int = 20) -> List[Dict[str, Any]]:
        """Search for Hajimi related videos"""
        try:
            print(f"Searching for '{keyword}' videos...")
            
            # Search for videos with the keyword
            result = await search.search_by_type(
                keyword=keyword,
                search_type=search.SearchObjectType.VIDEO,
                page=1,
                page_size=page_size,
                order_type=search.OrderVideo.TOTALRANK  # Sort by popularity
            )
            
            if not result:
                print("No search results found - empty result")
                return []
            
            # Handle different possible result structures
            if 'result' in result:
                videos = result['result']
            elif 'data' in result and 'result' in result['data']:
                videos = result['data']['result']
            else:
                print(f"Unexpected result structure: {list(result.keys())}")
                return []
            
            print(f"Found {len(videos)} videos")
            
            return videos
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
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
                
                # Extract the information we need
                video_data = {
                    'title': video_info.get('title', '').replace('<em class="keyword">', '').replace('</em>', ''),
                    'bvid': bvid,
                    'cover': video_info.get('pic', ''),
                    'view_count': detail.get('stat', {}).get('view', 0),
                    'url': f"https://www.bilibili.com/video/{bvid}"
                }
                
                detailed_videos.append(video_data)
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing video {video_info.get('bvid', 'unknown')}: {e}")
                continue
        
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

| 视频标题 (Title) | 封面 (Cover) | 播放量 (Views) |
|---|---|---|
"""
        
        for video in videos:
            title_with_link = f"[{video['title']}]({video['url']})"
            cover_img = f"![cover]({video['cover']})" if video['cover'] else "无封面"
            view_count = self.format_view_count(video['view_count'])
            
            content += f"| {title_with_link} | {cover_img} | {view_count} |\n"
        
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
            # Search for videos
            videos = await self.search_hajimi_videos()
            
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