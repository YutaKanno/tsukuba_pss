import requests  # Webページにアクセスするためのライブラリをインポートします
from bs4 import BeautifulSoup  # HTMLやXMLを解析するためのライブラリをインポートします

url = "https://baseball.omyutech.com/CupHomePageMember.action?gameId=20250868556"  # スクレイピングしたいWebページのURLを設定します

def scrape_stamem(url):
    try:
        response = requests.get(url)  # 指定されたURLにGETリクエストを送信し、サーバーからの応答（レスポンス）を取得します
        response.raise_for_status()  
        soup = BeautifulSoup(response.content, 'html.parser')

        sta_mem_top = soup.find('table', class_='mem-startmen')
        top_team = f"{soup.find('th', class_='member_header carp').text.strip()}学"
        if top_team == '日体大学':
            top_team = '日本体育大学'
        elif top_team == '桜美大学':
            top_team = '桜美林大学'
        elif top_team == '明学大学':
            top_team = '明治学院大学'
        elif top_team == '慶大学':
            top_team = '慶應義塾大学'
        elif top_team == '明大学':
            top_team = '明治大学'
        elif top_team == '早大学':
            top_team = '早稲田大学'
        elif top_team == '法大学':
            top_team = '法政大学'
        elif top_team == '立大学':
            top_team = '立教大学'
        elif top_team == '東大学':
            top_team = '東京大学'
        top_poses, top_names, top_nums, top_lrs = [], [], [], []
        pos_ja = ['捕', '一', '二', '三', '遊', '左', '中', '右', '指', '投']
        pos_num = [2,3,4,5,6,7,8,9,'D','P']
        for i in range(2, 11):
            top_pos_ja = sta_mem_top.find_all('tr')[i].find_all('td')[1].text.strip()
            for j in range(len(pos_ja)):
                if top_pos_ja == pos_ja[j]:
                    top_pos = pos_num[j]
            top_name = sta_mem_top.find_all('tr')[i].find_all('td')[2].text.strip().replace(' ', '')
            top_num = sta_mem_top.find_all('tr')[i].find_all('td')[3].text.strip() 
            if i == 11:
                top_lr = sta_mem_top.find_all('tr')[i].find_all('td')[5].text.strip()[0]
            else:
                top_lr = sta_mem_top.find_all('tr')[i].find_all('td')[5].text.strip()[2]
            
            top_poses.append(top_pos)
            top_names.append(top_name)
            top_nums.append(top_num)
            top_lrs.append(top_lr)
        
        # 六大, 神宮用にDHじゃないときにも対応させる
        try:
            i = 11
            top_pos_ja = sta_mem_top.find_all('tr')[i].find_all('td')[1].text.strip()
            for j in range(len(pos_ja)):
                if top_pos_ja == pos_ja[j]:
                    top_pos = pos_num[j]
            top_name = sta_mem_top.find_all('tr')[i].find_all('td')[2].text.strip().replace(' ', '')
            top_num = sta_mem_top.find_all('tr')[i].find_all('td')[3].text.strip() 
            if i == 11:
                top_lr = sta_mem_top.find_all('tr')[i].find_all('td')[5].text.strip()[0]
            else:
                top_lr = sta_mem_top.find_all('tr')[i].find_all('td')[5].text.strip()[2]
            
            top_poses.append(top_pos)
            top_names.append(top_name)
            top_nums.append(top_num)
            top_lrs.append(top_lr)
        except:
            for j in range(len(top_poses)):
                if top_poses[j] == 'P':
                    top_names.append(top_names[j])
                    top_nums.append(top_nums[j])
                    top_lrs.append(top_lrs[j])
            
        for i in range(len(pos_num)):
            for j in range(len(top_poses)):
                if top_poses[j] == pos_num[i]:
                    top_names.append(top_names[j])
                    top_nums.append(top_nums[j])
                    top_lrs.append(top_lrs[j])
            
            

        




        sta_mem_bottom = soup.find_all('table', class_='mem-startmen')[1]
        bottom_team = f"{soup.find('th', class_='member_header tigers').text.strip()}学"
        if bottom_team == '日体大学':
            bottom_team = '日本体育大学'
        elif bottom_team == '桜美大学':
            bottom_team = '桜美林大学'
        elif bottom_team == '明学大学':
            bottom_team = '明治学院大学'
        elif bottom_team == '慶大学':
            bottom_team = '慶應義塾大学'
        elif bottom_team == '明大学':
            bottom_team = '明治大学'
        elif bottom_team == '早大学':
            bottom_team = '早稲田大学'
        elif bottom_team == '法大学':
            bottom_team = '法政大学'
        elif bottom_team == '立大学':
            bottom_team = '立教大学'
        elif bottom_team == '東大学':
            bottom_team = '東京大学'
        bottom_poses, bottom_names, bottom_nums, bottom_lrs = [], [], [], []
        for i in range(2, 11):
            bottom_pos_ja = sta_mem_bottom.find_all('tr')[i].find_all('td')[1].text.strip()
            for j in range(len(pos_ja)):
                if bottom_pos_ja == pos_ja[j]:
                    bottom_pos = pos_num[j]
            bottom_name = sta_mem_bottom.find_all('tr')[i].find_all('td')[2].text.strip().replace(' ', '')
            bottom_num = sta_mem_bottom.find_all('tr')[i].find_all('td')[3].text.strip() 
            if i == 11:
                bottom_lr = sta_mem_bottom.find_all('tr')[i].find_all('td')[5].text.strip()[0]
            else:
                bottom_lr = sta_mem_bottom.find_all('tr')[i].find_all('td')[5].text.strip()[2]
            bottom_poses.append(bottom_pos)
            bottom_names.append(bottom_name)
            bottom_nums.append(bottom_num)
            bottom_lrs.append(bottom_lr)
        
        # 六大, 神宮用にDHじゃないときにも対応させる
        try:
            i = 11
            bottom_pos_ja = sta_mem_bottom.find_all('tr')[i].find_all('td')[1].text.strip()
            for j in range(len(pos_ja)):
                if bottom_pos_ja == pos_ja[j]:
                    bottom_pos = pos_num[j]
            bottom_name = sta_mem_bottom.find_all('tr')[i].find_all('td')[2].text.strip().replace(' ', '')
            bottom_num = sta_mem_bottom.find_all('tr')[i].find_all('td')[3].text.strip() 
            if i == 11:
                bottom_lr = sta_mem_bottom.find_all('tr')[i].find_all('td')[5].text.strip()[0]
            else:
                bottom_lr = sta_mem_bottom.find_all('tr')[i].find_all('td')[5].text.strip()[2]
            
            bottom_poses.append(bottom_pos)
            bottom_names.append(bottom_name)
            bottom_nums.append(bottom_num)
            bottom_lrs.append(bottom_lr)
        except:
            for j in range(len(bottom_poses)):
                if bottom_poses[j] == 'P':
                    bottom_names.append(bottom_names[j])
                    bottom_nums.append(bottom_nums[j])
                    bottom_lrs.append(bottom_lrs[j])
                    
        for i in range(len(pos_num)):
            for j in range(len(bottom_poses)):
                if bottom_poses[j] == pos_num[i]:
                    bottom_names.append(bottom_names[j])
                    bottom_nums.append(bottom_nums[j])
                    bottom_lrs.append(bottom_lrs[j])
    
        
        XX = 'success'
    
    
    
    
    
    
    except:
        top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, top_team, bottom_team = ['', '', '', '', '', '', '', '', '', 'P'], ["先攻1", "先攻2", "先攻3", "先攻4", "先攻5", "先攻6", "先攻7", "先攻8", "先攻9", "先攻P", "先攻C", "先攻1B", "先攻2B", "先攻3B", "先攻SS", "先攻LF", "先攻CF", "先攻RF", "先攻", "先攻"], ['', '', '', '', '', '', '', '', '', ''], ["右", "左", "右", "左", "右", "左", "右", "左", "右", "左", '右'], ['', '', '', '', '', '', '', '', '', 'P'], ["後攻1", "後攻2", "後攻3", "後攻4", "後攻5", "後攻6", "後攻7", "後攻8", "後攻9", "後攻P", "後攻C", "後攻1B", "後攻2B", "後攻3B", "後攻SS", "後攻LF", "後攻CF", "後攻RF", "後攻", "後攻"], ['', '', '', '', '', '', '', '', '', ''], ["左", "右", "左", "右", "左", "右", "左", "右", "左", "右", '右'], '先攻チーム', '後攻チーム'
        XX = 'not success'
        
        
    return top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, top_team, bottom_team, XX