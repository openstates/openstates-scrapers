#!/usr/bin/env ruby
require File.join(File.dirname(__FILE__), '..', 'rbutils', 'new_legislation')
require 'open-uri'
require 'hpricot'

class Wisconsin < LegislationScraper
  @@state = 'wi'
  

  def scrape_legislators(chamber, year)
    @words = {'lower' => 'REPRESENTATIVES', 'upper' => 'SENATORS'}
    #p "#{chamber} - #{year}"
    yr = year[2,4]
    path = "Prior%20Sessions/#{year}/indxauth#{yr}/"
    base = "http://nxt.legis.state.wi.us/nxt/gateway.dll?f=xmlcontents&command=getmore&basepathid=#{path}&direction=1&maxnodes=500&minnodesleft=500"
    doc = Hpricot(open(base))
    doc = (doc/"n[@t=#{@words[chamber]}]")
    path += doc.first['n']
    base = "http://nxt.legis.state.wi.us/nxt/gateway.dll?f=xmlcontents&command=getmore&basepathid=#{path}&direction=1&maxnodes=500&minnodesleft=500"
    doc = Hpricot(open(base)) / "n"
    critters = doc.map{|x| x['t']}
    critters.each{ |legislator|
      l = {:session => year, :chamber => chamber}
      l[:full_name] = legislator[/[\w\s\,\.\-]+/].strip.sub(/ (Rep.)|(Sen.) /,'')
      name = l[:full_name].split(',')
      (l[:first_name], l[:middle_name]) = name[1].split(' ').map{|x|x.sub('.','')}
      l[:last_name] = name[0]
      l[:district] = legislator[/\(\d{1,3}\w{2,3}/][1..-1]
      l.delete(:middle_name) unless l[:middle_name]
      add_legislator(l)
      #p legislator
    }
  end
  
  def scrape_bills(chamber, year)
    
  end
  
  
  def scrape_metadata
      {
      :state_name => 'Wisconsin',
      :legislature_name =>'The Wisconsin State Legislature',
      :lower_chamber_name =>'Assembly',
      :upper_chamber_name =>'Senate',
      :lower_title =>'Representative',
      :upper_title =>'Senator',
      :lower_term =>2,
      :upper_term =>4,
      :sessions => ['1989', 
                  '1991', '1993', '1995', '1997', '1999',
                  '2001', '2003', '2005', '2007', '2009'],
      :session_details => {
          '1989' =>{'years' =>[1989, 1990], 'sub_sessions' =>[]},
          '1991' =>{'years' =>[1991, 1992], 'sub_sessions' =>[]},
          '1993' =>{'years' =>[1993, 1994], 'sub_sessions' =>[]},
          '1995' =>{'years' =>[1995, 1996], 'sub_sessions' =>[]},
          '1997' =>{'years' =>[1997, 1998], 'sub_sessions' =>[]},
          '1999' =>{'years' =>[1999, 2000], 'sub_sessions' =>[]},
          '2001' =>{'years' =>[2001, 2002], 'sub_sessions' =>[]},
          '2003' =>{'years' =>[2003, 2004], 'sub_sessions' =>[]},
          '2005' =>{'years' =>[2005, 2006], 'sub_sessions' =>[]},
          '2007' =>{'years' =>[2007, 2008], 'sub_sessions' =>[]},
          '2009' =>{'years' =>[2009, 2010], 'sub_sessions' =>[]},
      }}
    end
end
Wisconsin.new.run

p 'ding'