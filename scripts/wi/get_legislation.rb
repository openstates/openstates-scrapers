#!/usr/bin/env ruby
require File.join(File.dirname(__FILE__), '..', 'rbutils', 'new_legislation')
require 'open-uri'
require 'hpricot'

class Wisconsin < LegislationScraper
  @@state = 'wi'
  

  def scrape_legislators(chamber, year)
    return
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
    details = {
      :state_name => 'Wisconsin',
      :legislature_name =>'The Wisconsin State Legislature',
      :lower_chamber_name =>'Assembly',
      :upper_chamber_name =>'Senate',
      :lower_title =>'Representative',
      :upper_title =>'Senator',
      :lower_term =>2,
      :upper_term =>4
    }
    
    doc = Hpricot(open('http://www.legis.state.wi.us/'))
    s = doc / "select[@id=session] option"
    sessions = []
    session_details = {}
    s.each{|sess|
      text = sess.inner_html
      if text =~ /^(\d{4})/
        year = $1.to_i
        sessions << year
        session_details[year] = {:years => [year, year+1], :sub_sessions => [] }
      elsif text =~ /\w\s(\d{4})/
        year = $1.to_i
        year -= 1 if year %2 == 0
        session_details[year][:sub_sessions] << text
      end 
    }
    details[:sessions] = sessions
    details[:session_details] = session_details

    return details
    end
end
Wisconsin.new.run